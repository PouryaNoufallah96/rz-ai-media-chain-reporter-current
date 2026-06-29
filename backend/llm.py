"""OpenRouter LLM helpers: chat (with JSON repair), image generation, and the
threaded single-editorial-model call. The OpenAI-SDK client is a process-wide
singleton here so all callers share one connection pool.
"""
import json
import re
import sys
import threading

import requests
import openai as _openai_sdk

from config import OPENROUTER_KEY, ORIGIN, OPENROUTER_IMAGE_MODELS


def _repair_json(raw):
    """Strip markdown fences, then parse JSON; if truncated, salvage partial content."""
    # Strip <think>...</think> reasoning blocks (DeepSeek and other reasoning models)
    s = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
    # Also handle unclosed <think> blocks (model cut off mid-reasoning)
    s = re.sub(r'<think>.*$', '', s, flags=re.DOTALL)
    s = s.strip()
    raw = s if s else raw
    # Strip ```json ... ``` or ``` ... ``` wrappers
    s = raw.strip()
    if s.startswith('```'):
        s = s.split('\n', 1)[-1]          # drop first line (```json)
        s = s.rsplit('```', 1)[0].strip() # drop closing ```
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        raw = s  # work on stripped version for repair attempts
    # Try appending common closing sequences to fix truncation
    for ending in (']}}}', ']}}', '}}', '}'):
        try:
            return json.loads(raw + ending)
        except json.JSONDecodeError:
            pass
    # Find the last complete `]` and close from there
    last_bracket = raw.rfind(']')
    if last_bracket > 0:
        trimmed = raw[:last_bracket + 1]
        for ending in ('}', '}}', '}}}'):
            try:
                return json.loads(trimmed + ending)
            except json.JSONDecodeError:
                pass
    # Also try stripping markdown fences that appear mid-string (model added preamble text)
    fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)```', raw)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Last resort: try every '{' position left-to-right until one parses
    # (handles reasoning models that prepend preamble text before the JSON)
    for m in re.finditer(r'\{', raw):
        candidate = raw[m.start():]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        for ending in (']}}}', ']}}', '}}', '}'):
            try:
                return json.loads(candidate + ending)
            except json.JSONDecodeError:
                pass

    # Model ignored the "respond with JSON" instruction and just wrote the post directly —
    # if there's no '{' anywhere, there's no JSON to recover; treat the prose itself as the copy.
    if '{' not in raw and raw.strip():
        return {'copy': raw.strip(), 'hashtags': []}

    preview = raw[:300].replace('\n', ' ')
    print(f'[JSON REPAIR FAILED] len={len(raw)} preview: {preview}', file=sys.stderr)
    raise ValueError(f'Could not parse or repair JSON response (len={len(raw)})')

_openrouter_client = None
_openrouter_client_lock = threading.Lock()
def _get_openrouter_client():
    global _openrouter_client
    if _openrouter_client is None:
        with _openrouter_client_lock:
            if _openrouter_client is None:
                _openrouter_client = _openai_sdk.OpenAI(
                    base_url='https://openrouter.ai/api/v1',
                    api_key=OPENROUTER_KEY,
                    default_headers={
                        'HTTP-Referer': ORIGIN if ORIGIN != '*' else 'https://chainreporter.app',
                        'X-Title':      'ChainReporter Editorial AI',
                    },
                    timeout=180,
                    max_retries=3,
                )
    return _openrouter_client

def openrouter_chat(model_id, messages, temperature=0.30, max_tokens=3500):
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')
    client = _get_openrouter_client()
    resp = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    raw = resp.choices[0].message.content or ''
    if not raw:
        finish = resp.choices[0].finish_reason
        raise ValueError(f'Model returned empty content (finish_reason={finish}). Try increasing max_tokens.')
    return _repair_json(raw)


def _editorial_call_one(model_key, model_cfg, system_prompt, user_prompt):
    """Called in a thread — returns (model_key, result_dict)."""
    msgs = [{'role': 'system', 'content': system_prompt},
            {'role': 'user',   'content': user_prompt}]
    try:
        result = openrouter_chat(model_cfg['id'], msgs, model_cfg['temperature'], model_cfg['max_tokens'])
        return model_key, {
            'model':  model_cfg['display'],
            'brands': result.get('brands', {}),
            'error':  None,
        }
    except Exception as exc:
        return model_key, {
            'model':  model_cfg['display'],
            'brands': {},
            'error':  str(exc),
        }

# ── OpenRouter image generation ───────────────────────────────────────────────
def openrouter_image(prompt, model, ref_images=None):
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')
    modalities = OPENROUTER_IMAGE_MODELS.get(model, ['image', 'text'])
    if ref_images:
        content = [{'type': 'text', 'text': prompt}]
        for img_url in ref_images:
            content.append({'type': 'image_url', 'image_url': {'url': img_url}})
    else:
        content = prompt
    r = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        json={
            'model': model,
            'messages': [{'role': 'user', 'content': content}],
            'modalities': modalities,
        },
        headers={
            'Authorization': f'Bearer {OPENROUTER_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': ORIGIN if ORIGIN != '*' else 'https://chainreporter.app',
            'X-Title': 'ChainReporter Editorial AI',
        },
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()
    msg = data['choices'][0]['message']
    images = msg.get('images') or []
    if images:
        data_url = images[0]['image_url']['url']   # "data:image/png;base64,..."
        if ',' in data_url:
            return data_url.split(',', 1)[1]       # strip the data: prefix
        return data_url
    # some models embed base64 directly in content
    content = msg.get('content', '')
    if content.startswith('data:'):
        return content.split(',', 1)[1] if ',' in content else content
    raise ValueError(f'No image returned by {model}. Response: {str(data)[:300]}')
