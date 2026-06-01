"""
ChainReporter Backend — Python 3.11
Runs on port 3001. Proxies all OpenAI and Google Apps Script calls server-side.
Start: python server.py
"""

import json
import os
import sys
import re
import hmac
import hashlib
import base64
import time
import random
import string
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import requests

# ── Load .env ──────────────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).parent / '.env'
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip())

OPENAI_KEY      = os.environ.get('OPENAI_API_KEY', '')
SCRIPT_URL      = os.environ.get('GOOGLE_APPS_SCRIPT_URL', '')
PORT            = int(os.environ.get('PORT', 3001))
ORIGIN          = os.environ.get('FRONTEND_ORIGIN', 'http://localhost:3000')
X_API_KEY       = os.environ.get('X_API_KEY', '')
X_API_SECRET    = os.environ.get('X_API_SECRET', '')
X_TOKEN         = os.environ.get('X_ACCESS_TOKEN', '')
X_TOKEN_SEC     = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
OPENROUTER_KEY   = os.environ.get('OPENROUTER_API_KEY', '')
TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL = os.environ.get('TELEGRAM_CHANNEL', '@chainreporternews')
TELEGRAM_PROXY   = os.environ.get('TELEGRAM_PROXY', '')   # e.g. http://127.0.0.1:10808
DRIVE_FOLDER_URL = os.environ.get('GOOGLE_DRIVE_FOLDER_URL', '')

OPENAI_CHAT     = 'https://api.openai.com/v1/chat/completions'
OPENAI_IMAGE    = 'https://api.openai.com/v1/images/generations'
OPENROUTER_URL  = 'https://openrouter.ai/api/v1/chat/completions'

# ── Editorial AI models ────────────────────────────────────────────────────────
# 'api': 'openai'    → calls OpenAI directly (uses OPENAI_KEY)
# 'api': 'openrouter' → calls OpenRouter (uses OPENROUTER_KEY)
EDITORIAL_MODELS = {
    'gpt': {
        'id':          'openai/gpt-5.5',
        'display':     'GPT-5.5',
        'temperature': 0.30,
        'max_tokens':  5500,
        'api':         'openrouter',
    },
    'gemini': {
        'id':          'google/gemini-3.1-pro-preview',
        'display':     'Gemini 3.1 Pro',
        'temperature': 0.30,
        'max_tokens':  16000,
        'api':         'openrouter',
    },
    'claude': {
        'id':          'anthropic/claude-opus-4-7',
        'display':     'Claude Opus 4.7',
        'temperature': 0.30,
        'max_tokens':  8000,
        'api':         'openrouter',
    },
    'deepseek': {
        'id':          'deepseek/deepseek-v4-flash',
        'display':     'DeepSeek V4 Flash',
        'temperature': 0.30,
        'max_tokens':  8000,
        'api':         'openrouter',
    },
}

# ── Platform rules ─────────────────────────────────────────────────────────────
PLAT_RULES = {
    'X': {
        'maxChars': 280, 'maxTokens': 180, 'temperature': 0.20,
        'system': lambda brand, sent: (
            f'You are the social media editor for {brand}, a premium crypto news brand. Sentiment: {sent}.\n'
            'Write a single punchy news-wire tweet.\n'
            'HARD RULE: response must be ≤ 280 characters total including spaces and hashtags.\n'
            'Use 2-3 relevant hashtags. No emojis. Journalist tone. Start with the news hook.\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1","#Tag2"] }'
        ),
    },
    'Telegram': {
        'maxChars': 4096, 'maxTokens': 700, 'temperature': 0.28,
        'system': lambda brand, sent: (
            f'You are the Telegram channel editor for {brand}. Sentiment: {sent}.\n'
            'Write a full channel post: 2-4 paragraphs. Include context, implications, key figures.\n'
            'End with a brand-voice closing line and 3-5 hashtags.\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }'
        ),
    },
    'Instagram': {
        'maxChars': 2200, 'maxTokens': 700, 'temperature': 0.32,
        'system': lambda brand, sent: (
            f'You are the Instagram editor for {brand}. Sentiment: {sent}.\n'
            'Write a visual-first caption: strong opening hook, storytelling body, clear CTA.\n'
            'Use 5-10 discovery hashtags at the end. Light use of relevant emojis.\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }'
        ),
    },
}

# ── Brand visual tones for image generation ─────────────────────────────────
BRAND_VISUAL_TONE = {
    'RZ Prime':        'sleek dark-mode financial newsroom, deep blue and gold palette, cinematic editorial',
    'Coin Hall':       'modern crypto trading floor, green accents, data-driven, sharp professional',
    'ChainReporter':   'blockchain technology, teal and violet aurora aesthetic, futuristic journalism',
    'Meta Coin Guard': 'security-focused, dark red and black, cybersecurity intelligence, shield motifs',
}

# ── OpenAI helpers ─────────────────────────────────────────────────────────────
def openai_chat(messages, temperature, max_tokens, model='gpt-4o-mini'):
    if not OPENAI_KEY:
        raise ValueError('OPENAI_API_KEY not set in .env')
    r = requests.post(OPENAI_CHAT, json={
        'model': model,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
        'messages': messages,
    }, headers={'Authorization': f'Bearer {OPENAI_KEY}'}, timeout=120)
    r.raise_for_status()
    return _repair_json(r.json()['choices'][0]['message']['content'])

def openai_image(prompt, model='dall-e-3', size='1792x1024'):
    if not OPENAI_KEY:
        raise ValueError('OPENAI_API_KEY not set in .env')
    is_gpt_image = model.startswith('gpt-image') or model.startswith('chatgpt-image')
    if is_gpt_image:
        payload = {
            'model':   model,
            'prompt':  prompt,
            'n':       1,
            'size':    '1536x1024',
            'quality': 'high',
        }
    elif model == 'dall-e-2':
        payload = {
            'model':           model,
            'prompt':          prompt,
            'n':               1,
            'size':            '1024x1024',
            'response_format': 'b64_json',
        }
    else:  # dall-e-3
        payload = {
            'model':           model,
            'prompt':          prompt,
            'n':               1,
            'size':            size,
            'quality':         'hd',
            'response_format': 'b64_json',
        }
    r = requests.post(OPENAI_IMAGE, json=payload,
                      headers={'Authorization': f'Bearer {OPENAI_KEY}'}, timeout=120)
    r.raise_for_status()
    item = r.json()['data'][0]
    if 'b64_json' in item:
        return item['b64_json']
    # gpt-image family may return a URL — fetch and convert
    img_r = requests.get(item['url'], timeout=60)
    img_r.raise_for_status()
    return base64.b64encode(img_r.content).decode()

# ── Apps Script helper ─────────────────────────────────────────────────────────
def call_apps_script(payload):
    if not SCRIPT_URL or SCRIPT_URL.startswith('PASTE_'):
        raise ValueError('GOOGLE_APPS_SCRIPT_URL not configured in .env')
    r = requests.post(SCRIPT_URL, json=payload,
                      headers={'Content-Type': 'application/json'},
                      allow_redirects=True, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get('success'):
        raise ValueError(data.get('error', 'Apps Script returned failure'))
    return data

# ── Route handlers ─────────────────────────────────────────────────────────────
def handle_generate_copy(body):
    article   = body.get('article', {})
    platform  = body.get('platform', '')
    media     = body.get('mediaBrand', '')
    sentiment = body.get('sentiment', 'Neutral')
    model_key = body.get('modelKey', 'gpt')   # 'gpt' | 'gemini' | 'claude'

    if not article or not platform or not media:
        raise ValueError('Missing article, platform, or mediaBrand')

    rule = PLAT_RULES.get(platform)
    if not rule:
        raise ValueError(f'Unknown platform: {platform}')

    user_msg = (
        f"Article title: {article.get('title', '')}\n"
        f"Source: {article.get('source', '')}\n"
        f"Description: {article.get('desc', '')}\n"
        f"Keywords: {', '.join(article.get('matchedKeywords', []))}"
    )

    def call(extra=''):
        sys_prompt = rule['system'](media, sentiment)
        if extra:
            sys_prompt += '\n' + extra
        msgs = [{'role': 'system', 'content': sys_prompt},
                {'role': 'user',   'content': user_msg}]
        if model_key in ('gemini', 'claude'):
            cfg = EDITORIAL_MODELS[model_key]
            return openrouter_chat(cfg['id'], msgs, rule['temperature'], rule['maxTokens'])
        else:
            return openai_chat(msgs, rule['temperature'], rule['maxTokens'])

    result   = call()
    copy     = result.get('copy', '')
    hashtags = result.get('hashtags', [])

    if platform == 'X' and len(copy) > 280:
        over   = len(copy)
        result = call(f'IMPORTANT: Your previous attempt was {over} characters. You MUST fit within 280. Cut aggressively.')
        copy     = result.get('copy', copy)
        hashtags = result.get('hashtags', hashtags)
        if len(copy) > 280:
            copy = copy[:277] + '…'

    return {'copy': copy, 'hashtags': hashtags, 'charCount': len(copy), 'platform': platform}


def handle_generate_image(body):
    article   = body.get('article', {})
    platform  = body.get('platform', 'X')
    media     = body.get('mediaBrand', 'ChainReporter')
    sentiment = body.get('sentiment', 'Neutral')
    model     = body.get('model', 'dall-e-3')
    size      = body.get('size', '1792x1024')

    tone     = BRAND_VISUAL_TONE.get(media, 'premium crypto news, dark cinematic aesthetic')
    sent_tone = ('optimistic upward energy, green tones' if sentiment == 'Bullish'
                 else 'tense cautionary mood, red accents' if sentiment == 'Bearish'
                 else 'balanced neutral editorial')

    prompt = (
        f'Hyper-realistic editorial photo illustration for a premium crypto news brand. '
        f'Story: {article.get("title", "")}. '
        f'Visual tone: {tone}. Mood: {sent_tone}. '
        f'Platform: {platform} post — {"square-friendly, bold visual" if platform == "Instagram" else "wide cinematic banner"}. '
        'No text overlays. No logos. No people unless implied by silhouette. '
        'Style: professional financial journalism photography, ultra-high-detail, dramatic lighting.'
    )

    image_b64 = openai_image(prompt, model, size)
    return {'imageB64': image_b64, 'prompt': prompt, 'model': model}


def handle_proxy_chat(body):
    """Generic proxy — frontend sends full OpenAI-shaped request, backend adds the key."""
    if not OPENAI_KEY:
        raise ValueError('OPENAI_API_KEY not set in .env')
    r = requests.post(OPENAI_CHAT, json=body,
                      headers={'Authorization': f'Bearer {OPENAI_KEY}'}, timeout=120)
    r.raise_for_status()
    return r.json()


def handle_sheets(action, body):
    payload = {'action': action, **body}
    if action == 'uploadImage' and 'driveFolder' not in payload and DRIVE_FOLDER_URL:
        payload['driveFolder'] = DRIVE_FOLDER_URL
    return call_apps_script(payload)


def handle_telegram_post(body):
    if not TELEGRAM_TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN not set in .env')
    image_b64 = body.get('imageB64', '')
    headline  = body.get('headline', '')
    copy_text = body.get('copy', '')
    hashtags  = body.get('hashtags', [])
    link      = body.get('link', '')
    tg_base   = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'
    tg_proxies = {'https': TELEGRAM_PROXY} if TELEGRAM_PROXY else None

    hashtag_line = ' '.join(hashtags)
    source_line  = f'\n\n🔗 {link}' if link and link != '#' else ''
    full_text    = '\n\n'.join(filter(None, [copy_text, hashtag_line, source_line.strip()]))

    if image_b64:
        img_bytes = base64.b64decode(image_b64)
        safe_headline = re.sub(r'([*_`\[\]])', r'\\\1', headline)
        # Build suffix (hashtags + link) — always kept intact
        suffix_parts = [p for p in [hashtag_line, source_line.strip()] if p]
        suffix = '\n\n'.join(suffix_parts)
        head = f'*{safe_headline}*' if safe_headline else ''
        # How much room is left for the body copy?
        # Format: head + \n\n + copy + \n\n + suffix  (omit empty parts)
        overhead = len(head) + (2 if head else 0) + (2 + len(suffix) if suffix else 0)
        available = 1024 - overhead
        body = copy_text[:available].rstrip() if len(copy_text) > available else copy_text
        if body and len(copy_text) > available:
            body = body[:body.rfind(' ')] + '…' if ' ' in body else body + '…'
        parts = [p for p in [head, body, suffix] if p]
        caption = '\n\n'.join(parts)
        r = requests.post(f'{tg_base}/sendPhoto',
                          data={'chat_id': TELEGRAM_CHANNEL, 'caption': caption,
                                'parse_mode': 'Markdown'},
                          files={'photo': ('image.png', img_bytes, 'image/png')},
                          proxies=tg_proxies, timeout=60)
        r.raise_for_status()
        result = r.json()
        if not result.get('ok'):
            raise ValueError(result.get('description', 'Telegram sendPhoto failed'))
        return result
    else:
        # Escape special Markdown chars for the bold headline
        safe_headline = re.sub(r'([*_`\[\]])', r'\\\1', headline)
        message = f'*{safe_headline}*\n\n{full_text}' if safe_headline else full_text
        r = requests.post(f'{tg_base}/sendMessage',
                          data={'chat_id': TELEGRAM_CHANNEL, 'text': message,
                                'parse_mode': 'Markdown',
                                'disable_web_page_preview': 'false'},
                          proxies=tg_proxies, timeout=30)
        r.raise_for_status()
        result = r.json()
        if not result.get('ok'):
            raise ValueError(result.get('description', 'Telegram sendMessage failed'))
        return result


# ── X (Twitter) OAuth 1.0a ─────────────────────────────────────────────────────
def _oauth_header(method, url, extra_params, consumer_key, consumer_secret, token, token_secret):
    nonce     = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    timestamp = str(int(time.time()))
    oauth = {
        'oauth_consumer_key':     consumer_key,
        'oauth_nonce':            nonce,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp':        timestamp,
        'oauth_token':            token,
        'oauth_version':          '1.0',
    }
    all_params = {**extra_params, **oauth}
    enc = lambda s: urllib.parse.quote(str(s), safe='')
    param_str = '&'.join(f'{enc(k)}={enc(v)}' for k, v in sorted(all_params.items()))
    base = '&'.join([method.upper(), enc(url), enc(param_str)])
    key  = f'{enc(consumer_secret)}&{enc(token_secret)}'
    sig  = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth['oauth_signature'] = sig
    return 'OAuth ' + ', '.join(f'{enc(k)}="{enc(v)}"' for k, v in sorted(oauth.items()))


def handle_twitter_post(body):
    if not all([X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC]):
        raise ValueError('X API credentials not fully configured in .env')
    if X_TOKEN.startswith('PASTE_') or X_TOKEN_SEC.startswith('PASTE_'):
        raise ValueError('X Access Token not yet set — paste real values in .env')

    image_b64 = body.get('imageB64', '')
    copy_text = body.get('copy', '')
    hashtags  = body.get('hashtags', [])
    hashtag_str = ' '.join(hashtags) if isinstance(hashtags, list) else str(hashtags)
    tweet_text = f'{copy_text}\n\n{hashtag_str}'.strip()
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + '…'

    media_id = None
    if image_b64:
        upload_url = 'https://upload.twitter.com/1.1/media/upload.json'
        auth = _oauth_header('POST', upload_url, {}, X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC)
        # multipart keeps the large base64 out of the OAuth signature base string
        ur = requests.post(upload_url,
                           files=[('media_data', (None, image_b64))],
                           headers={'Authorization': auth}, timeout=90)
        ur.raise_for_status()
        media_id = ur.json().get('media_id_string')

    tweet_url = 'https://api.twitter.com/2/tweets'
    auth = _oauth_header('POST', tweet_url, {}, X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC)
    tweet_body = {'text': tweet_text}
    if media_id:
        tweet_body['media'] = {'media_ids': [media_id]}
    tr = requests.post(tweet_url, json=tweet_body,
                       headers={'Authorization': auth, 'Content-Type': 'application/json'},
                       timeout=30)
    tr.raise_for_status()
    data = tr.json()
    return {'success': True, 'tweetId': data.get('data', {}).get('id', ''), 'mediaId': media_id}


# ── JSON repair helper (handles truncated responses and markdown fences) ───────
def _repair_json(raw):
    """Strip markdown fences, then parse JSON; if truncated, salvage partial content."""
    # Strip <think>...</think> reasoning blocks (DeepSeek and other reasoning models)
    s = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
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

    raise ValueError(f'Could not parse or repair JSON response (len={len(raw)})')


# ── OpenRouter helper (uses openai SDK for robust threading/chunked support) ───
import openai as _openai_sdk

_openrouter_client = None
def _get_openrouter_client():
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = _openai_sdk.OpenAI(
            base_url='https://openrouter.ai/api/v1',
            api_key=OPENROUTER_KEY,
            default_headers={
                'HTTP-Referer': 'http://localhost:3000',
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
        if model_cfg.get('api') == 'openai':
            result = openai_chat(msgs, model_cfg['temperature'], model_cfg['max_tokens'], model=model_cfg['id'])
        else:
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


def handle_editorial_select(body):
    shortlist      = body.get('shortlist', [])
    sel_media      = body.get('selectedMedia', [])
    sel_plats      = body.get('selectedPlatforms', ['X', 'Telegram', 'Instagram'])
    topics         = body.get('topics', '').strip()

    if not shortlist:
        raise ValueError('shortlist is empty')
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')

    # Build compact article list for the prompt
    lines = []
    for a in shortlist:
        s   = a.get('scores', {})
        r   = a.get('routing', {})
        idx = a.get('input_index', 0)
        desc = (a.get('desc') or '')[:220].replace('\n', ' ')
        lines.append(
            f"[{idx}] {a.get('source','')} | "
            f"Score:{s.get('final',0)} Vir:{s.get('virality',0)} "
            f"Fresh:{s.get('freshness',0)} Auth:{s.get('authority',0)} "
            f"Brand→{r.get('primary_media','')}\n"
            f"    \"{a.get('title','')}\"\n"
            f"    {a.get('link','')}\n"
            f"    {desc}"
        )
    article_text = '\n\n'.join(lines)

    brand_list = ', '.join(sel_media) if sel_media else 'any'
    plat_list  = ', '.join(sel_plats)
    topic_line = f'Topic focus: {topics}' if topics else 'No specific topic filter — use your editorial judgment.'

    brand_descs = {
        'RZ Prime':        'Token Access · BNB Chain · Smart Contracts · Retail Investors',
        'Coin Hall':       'Luxury · Web3 Culture · High-End Experiences · Aspirational',
        'ChainReporter':   'Full Spectrum Crypto · Markets · Policy · Technology · Culture',
        'Meta Coin Guard': 'Security · DeFi Protection · Exploits · Wallet Safety · Risk Awareness',
    }
    brand_descs_text = '\n'.join(
        f'  - {m}: {brand_descs.get(m, "Crypto media brand")}' for m in sel_media
    )
    article_schema = (
        '{"input_index":<N>,"platform":"<platform>",'
        '"title":"<exact title>","source":"<source>","source_url":"<url>",'
        '"selection_reason":"<why>","copy":"<post copy>",'
        '"hashtags":["#Tag"],'
        '"suitability_score":<0-100>,"impact_score":<0-100>,'
        '"virality_score":<0-100>,"confidence_score":<0-100>}'
    )
    system_prompt = (
        'You are a senior crypto news editor making independent editorial decisions for social media publishing.\n'
        f'Available platforms: {plat_list}\n\n'
        f'Media brands you must cover:\n{brand_descs_text}\n\n'
        'Your task: For EACH media brand listed above, independently select the BEST 5 articles '
        'from the shortlist that fit that brand\'s identity. '
        'An article may appear in multiple brands if genuinely relevant to both.\n'
        'Base your judgment on: news value, real-world impact, brand fit, virality potential, freshness, and topic relevance.\n'
        'Each model is making this selection independently — bring your own editorial perspective.\n\n'
        'For each selected article:\n'
        '- Use the EXACT input_index from the [N] marker in the list\n'
        '- Assign the best matching platform\n'
        '- Write a selection_reason (1-2 sentences, your editorial reasoning for THIS brand)\n'
        '- Write platform-appropriate copy (tweet ≤280 chars for X, longer post for Telegram/Instagram)\n'
        '- Provide 3-5 relevant hashtags\n'
        '- Score suitability/impact/virality/confidence 0-100\n\n'
        'Respond ONLY with valid JSON — one key per brand, each value an array of exactly 5 article objects:\n'
        '{"brands":{'
        f'"<brand_name>":[{article_schema},...5 items],'
        '"<next_brand>":[...5 items]'
        '}}'
    )
    user_prompt = f'{topic_line}\n\nShortlisted articles ({len(shortlist)} total):\n\n{article_text}'

    sel_models   = body.get('selectedModels', list(EDITORIAL_MODELS.keys()))
    active_models = {k: v for k, v in EDITORIAL_MODELS.items() if k in sel_models}
    if not active_models:
        active_models = EDITORIAL_MODELS  # fallback: use all

    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = {}
    with ThreadPoolExecutor(max_workers=len(active_models)) as pool:
        futures = {
            pool.submit(_editorial_call_one, k, v, system_prompt, user_prompt): k
            for k, v in active_models.items()
        }
        for fut in as_completed(futures):
            key, data = fut.result()
            results[key] = data

    return results


# ── HTTP Request Handler ───────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'[{self.command}] {self.path} — {args[1] if len(args) > 1 else ""}')

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', ORIGIN)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self._json({'ok': True})
        else:
            self._error(404, 'Not found')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        raw    = self.rfile.read(length)
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return self._error(400, 'Invalid JSON')

        try:
            path = self.path.rstrip('/')
            if path == '/api/proxy/chat':
                self._json(handle_proxy_chat(body))
            elif path == '/api/copy/generate':
                self._json(handle_generate_copy(body))
            elif path == '/api/image/generate':
                self._json(handle_generate_image(body))
            elif path == '/api/sheets/approve':
                self._json(handle_sheets('approve', body))
            elif path == '/api/sheets/schedule':
                self._json(handle_sheets('schedule', body))
            elif path == '/api/sheets/update':
                self._json(handle_sheets('update', body))
            elif path == '/api/sheets/upload-image':
                self._json(handle_sheets('uploadImage', body))
            elif path == '/api/twitter/post':
                self._json(handle_twitter_post(body))
            elif path == '/api/ai/editorial-select':
                self._json(handle_editorial_select(body))
            elif path == '/api/telegram/post':
                self._json(handle_telegram_post(body))
            else:
                self._error(404, f'Unknown route: {path}')
        except ValueError as e:
            self._error(400, str(e))
        except requests.HTTPError as e:
            self._error(502, f'Upstream error: {e}')
        except Exception as e:
            print(f'[ERROR] {e}', file=sys.stderr)
            self._error(500, str(e))

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        self._json({'error': msg}, code)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not OPENAI_KEY:
        print('[WARN] OPENAI_API_KEY not set — AI routes will fail', file=sys.stderr)
    if not SCRIPT_URL or SCRIPT_URL.startswith('PASTE_'):
        print('[WARN] GOOGLE_APPS_SCRIPT_URL not set — Sheets routes will fail', file=sys.stderr)

    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'ChainReporter backend running at http://localhost:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
