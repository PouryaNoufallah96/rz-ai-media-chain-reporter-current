"""
ChainReporter Backend — Python 3.11
Runs on port 3001. Proxies all OpenRouter (AI) and Google Apps Script calls server-side.
Start: python server.py
"""

import json
import gzip
import threading
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
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import requests
from datetime import datetime as _datetime, date as _date

try:
    from filtering.pipeline import run_pipeline as _run_pipeline
    _FILTERING_AVAILABLE = True
except ImportError as _e:
    print(f'[WARN] filtering package not available: {_e}', file=sys.stderr)
    _FILTERING_AVAILABLE = False

try:
    from filtering.deepseek_pipeline import run_deepseek_pipeline as _run_deepseek_pipeline
    _DEEPSEEK_FILTER_AVAILABLE = True
except ImportError as _e2:
    print(f'[WARN] deepseek_pipeline not available: {_e2}', file=sys.stderr)
    _DEEPSEEK_FILTER_AVAILABLE = False

# ── JSON helper: handle datetime + numpy scalars ──────────────────────────────
def _json_default(obj):
    if isinstance(obj, (_datetime, _date)):
        return obj.isoformat()
    try:
        import numpy as _np
        if isinstance(obj, _np.integer): return int(obj)
        if isinstance(obj, _np.floating): return float(obj)
        if isinstance(obj, _np.ndarray): return obj.tolist()
    except ImportError:
        pass
    raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')


# ── Load .env ──────────────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).parent / '.env'
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip())

SCRIPT_URL      = os.environ.get('GOOGLE_APPS_SCRIPT_URL', '')
PORT            = int(os.environ.get('PORT', 3001))
ORIGIN          = os.environ.get('FRONTEND_ORIGIN', '*')
X_API_KEY       = os.environ.get('X_API_KEY', '')
X_API_SECRET    = os.environ.get('X_API_SECRET', '')
X_TOKEN         = os.environ.get('X_ACCESS_TOKEN', '')
X_TOKEN_SEC     = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
OPENROUTER_KEY   = os.environ.get('OPENROUTER_API_KEY', '')
TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL = os.environ.get('TELEGRAM_CHANNEL', '@chainreporternews')
TELEGRAM_PROXY   = os.environ.get('TELEGRAM_PROXY', '')   # e.g. http://127.0.0.1:10808
DRIVE_FOLDER_URL = os.environ.get('GOOGLE_DRIVE_FOLDER_URL', '')

OPENROUTER_URL  = 'https://openrouter.ai/api/v1/chat/completions'

# ── Editorial AI models (all routed through OpenRouter) ───────────────────────
EDITORIAL_MODELS = {
    'gpt': {
        'id':          'openai/gpt-5.5',
        'display':     'GPT-5.5',
        'temperature': 0.30,
        'max_tokens':  16000,
        'api':         'openrouter',
    },
    'gemini': {
        'id':          'google/gemini-3.1-pro-preview',
        'display':     'Gemini 3.1 Pro Preview',
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
        'max_tokens':  16000,
        'api':         'openrouter',
    },
    'grok': {
        'id':          'x-ai/grok-4.3',
        'display':     'Grok 4.3',
        'temperature': 0.30,
        'max_tokens':  16000,
        'api':         'openrouter',
    },
}

# ── Platform rules ─────────────────────────────────────────────────────────────
# ── Topic-anchored emoji suggestions (keeps emoji placement semantic, not random) ──
EMOJI_LEXICON = {'markets': '📈📉', 'crypto': '₿🪙', 'politics': '🏛️🗳️', 'breaking': '🚨⚡️'}
_EMOJI_HINT = ', '.join(f'{k}→{v}' for k, v in EMOJI_LEXICON.items())

_FACT_RULE = 'HARD RULE: use only facts present in the provided article. Do not invent figures, quotes, names, or outcomes.'

def _sibling_block(sibling_copy, other_label):
    if not sibling_copy:
        return ''
    return (f'\nFor reference, here is the {other_label} version already published for this same story — '
            f'make this version structurally and tonally distinct, not a re-flow of it:\n"{sibling_copy}"')

PLAT_RULES = {
    'X': {
        'maxChars': 280, 'maxTokens': 500, 'temperature': 0.35,
        'emoji_policy': 'none — zero emojis, journalist tone only',
        'system': lambda brand, sent, sibling_copy=None: (
            f'You are the senior social media editor for {brand}, a premium crypto news brand, known for scroll-stopping one-liners. Sentiment: {sent}.\n'
            'PERSONA: sharp, fast, opinionated-but-factual — the post a trader screenshots before reading the full article.\n'
            'STRUCTURE: one scroll-stopping unit — a hook line that states the news, optionally one short line of context/stakes, then 2-3 hashtags that matter for reach (ticker/topic tags, not generic ones).\n'
            'HARD RULE: response must be ≤ 280 characters total including spaces and hashtags.\n'
            'EMOJI POLICY: none — zero emojis on X, ever.\n'
            f'{_FACT_RULE}\n'
            'EXAMPLES OF THE VOICE (do not reuse content, only mirror tone/structure):\n'
            '- "BlackRock just filed for a spot Solana ETF. The Bitcoin ETF playbook is repeating — and this time the SEC clock is already ticking. #Solana #ETF"\n'
            '- "Binance freezes $80M in wallets linked to a North Korean laundering ring. Compliance teams everywhere just got a new case study. #Binance #Crypto"\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1","#Tag2"] }'
            + _sibling_block(sibling_copy, 'X')
        ),
        'variant_angles': [
            {'label': 'Breaking', 'instruction': 'ANGLE: lead with urgency and the key number — one scroll-stopping hook framed as urgent, breaking news.'},
            {'label': 'Question', 'instruction': 'ANGLE: open or close with one genuine question that invites replies — make the reader want to respond, not just read.'},
            {'label': 'Take',     'instruction': 'ANGLE: one confident, opinionated-but-factual framing — sharp analysis, not hype.'},
        ],
    },
    'Telegram': {
        'minChars': 300, 'maxChars': 600, 'maxTokens': 700, 'temperature': 0.5,
        'emoji_policy': 'sparing, structural — e.g. 📌 for bullet markers, 🚨 only for genuinely breaking news',
        'system': lambda brand, sent, sibling_copy=None: (
            f'You are the Telegram channel editor for {brand}, writing for an audience that wants the full story without leaving the app. Sentiment: {sent}.\n'
            'PERSONA: a newswire desk — calm, thorough, slightly more candid than the brand\'s public tweets.\n'
            'STRUCTURE: a bold headline line, then a short body (2-3 tight paragraphs covering what happened, why it matters, and what to watch), then optional 📌 bullet points for key figures/dates, then a closing source-attribution line.\n'
            'HARD RULE: response must be 300-600 characters total, including spaces, line breaks, emoji and hashtags.\n'
            'EMOJI POLICY: sparing and structural — 📌 for bullets, 🚨 only for breaking news, nothing decorative.\n'
            f'Suggested topic→emoji anchors (use only if relevant, never force them): {_EMOJI_HINT}.\n'
            f'{_FACT_RULE}\n'
            'EXAMPLE OF THE VOICE (do not reuse content, only mirror tone/structure):\n'
            '"**Coinbase adds institutional staking for Solana**\\n\\nCoinbase confirmed Tuesday that institutional clients can now stake SOL directly through its custody platform, joining a wave of exchanges chasing yield-hungry funds.\\n\\nThe move comes as on-chain staking volume hits a 2026 high, and could pressure smaller custodians to follow.\\n\\n📌 Minimum stake: $50K\\n📌 Live in: US, EU, Singapore\\n\\nSource: Coinbase press desk · #Solana #Staking #Institutional"\n'
            'End with 3-5 hashtags (can be folded into the source line as shown above).\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }'
            + _sibling_block(sibling_copy, 'X')
        ),
        'variant_angles': [
            {'label': 'Newswire',   'instruction': 'ANGLE: strict newswire brief — bold headline, 2-3 factual sentences, source line. No opinion or interpretation.'},
            {'label': 'Analysis',   'instruction': 'ANGLE: calm analytical tone — explain what this means and why it matters, more interpretive than a wire brief.'},
            {'label': 'Key points', 'instruction': 'ANGLE: bold headline followed by 3 concise 📌 bullet points covering the key figures/facts, then a closing source line.'},
        ],
    },
    'Instagram': {
        'maxChars': 2200, 'maxTokens': 700, 'temperature': 0.4,
        'emoji_policy': 'liberal but purposeful, semantically matched to topic — never decorative spam',
        'system': lambda brand, sent, sibling_copy=None: (
            f'You are the Instagram editor for {brand}, writing captions for a visual-first, scroll-fast audience. Sentiment: {sent}.\n'
            'PERSONA: energetic storyteller — makes a market headline feel like a moment worth stopping for.\n'
            'STRUCTURE: a strong opening hook line, a short storytelling body that builds context and stakes, a clear closing CTA (e.g. "Tap in for the full breakdown" / "Where do you stand?"), then a block of 5-10 discovery hashtags.\n'
            'EMOJI POLICY: liberal but purposeful — pick emojis that semantically match the topic, never spam the same emoji repeatedly.\n'
            f'Suggested topic→emoji anchors (use only if relevant): {_EMOJI_HINT}.\n'
            f'{_FACT_RULE}\n'
            'EXAMPLE OF THE VOICE (do not reuse content, only mirror tone/structure):\n'
            '"Ethereum just flipped a 3-year resistance level into support 📈\\n\\nWhile most were watching Bitcoin, ETH quietly built the kind of base that precedes real moves — and on-chain data shows whales are accumulating again.\\n\\nIs this the setup before the next leg up, or another fakeout? Drop your call below 👇\\n\\n#Ethereum #ETH #CryptoMarkets #Web3 #OnChainData #BullMarket #DeFi"\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }'
            + _sibling_block(sibling_copy, 'X')
        ),
    },
}

# ── Emoji cleanup: collapse runs and cap counts per platform ──────────────────
_EMOJI_RE = re.compile(
    '([\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF])'
)
_EMOJI_CAP = {'X': 0, 'Telegram': 3, 'Instagram': 8}

def clean_emojis(text, platform):
    if not text:
        return text
    # collapse runs of 3+ identical emoji into a single instance
    text = re.sub(r'(' + _EMOJI_RE.pattern + r')\1{2,}', r'\1', text)
    cap = _EMOJI_CAP.get(platform)
    if cap is None:
        return text
    seen = 0
    out = []
    for ch in text:
        if _EMOJI_RE.fullmatch(ch):
            if seen >= cap:
                continue
            seen += 1
        out.append(ch)
    return ''.join(out)

def smart_truncate(text, limit=280):
    """Cut to the last full word/token (never mid-word, mid-hashtag, or mid-$TICKER)."""
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(' ', 1)[0]
    return cut.rstrip(' .,;:–—-') + '…'

# ── Brand visual tones for image generation ─────────────────────────────────
BRAND_VISUAL_TONE = {
    'RZ Prime':        'sleek dark-mode financial newsroom, deep blue and gold palette, cinematic editorial',
    'Coin Hall':       'modern crypto trading floor, green accents, data-driven, sharp professional',
    'ChainReporter':   'blockchain technology, teal and violet aurora aesthetic, futuristic journalism',
    'Meta Coin Guard': 'security-focused, dark red and black, cybersecurity intelligence, shield motifs',
}

# ── OpenRouter image generation ───────────────────────────────────────────────
# Models that use the OpenRouter chat/completions endpoint with modalities:["image"]
OPENROUTER_IMAGE_MODELS = {
    'x-ai/grok-imagine-image-quality':      ['image'],
    'google/gemini-3.1-flash-image-preview':['image', 'text'],
    'google/gemini-3-pro-image-preview':    ['image', 'text'],
    'openai/gpt-5.4-image-2':              ['image', 'text'],
    'recraft/recraft-v4-pro':              ['image'],
}

def openrouter_image(prompt, model):
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')
    modalities = OPENROUTER_IMAGE_MODELS.get(model, ['image', 'text'])
    r = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        json={
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
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
    article      = body.get('article', {})
    platform     = body.get('platform', '')
    media        = body.get('mediaBrand', '')
    sentiment    = body.get('sentiment', 'Neutral')
    model_key    = body.get('modelKey', 'gpt')   # 'gpt' | 'gemini' | 'claude'
    sibling_copy = body.get('siblingCopy') or None
    variant_count = max(1, min(3, body.get('variantCount', 2)))

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
        sys_prompt = rule['system'](media, sentiment, sibling_copy)
        if extra:
            sys_prompt += '\n' + extra
        msgs = [{'role': 'system', 'content': sys_prompt},
                {'role': 'user',   'content': user_msg}]
        cfg = EDITORIAL_MODELS.get(model_key, EDITORIAL_MODELS['gpt'])
        return openrouter_chat(cfg['id'], msgs, rule['temperature'], rule['maxTokens'])

    def safe_call(extra=''):
        """One retry on a malformed/unparseable model response — most JSON misses are one-off hiccups,
        and a single bad variant shouldn't fail the whole batch (the user sees 'nothing generated')."""
        try:
            return call(extra)
        except ValueError:
            return call(extra)

    angles = rule.get('variant_angles')

    def _enforce_length(copy, hashtags, extra=''):
        """Re-roll toward the platform's char-count bounds; hard-truncate over the max as a last resort."""
        lo, hi = rule.get('minChars'), rule.get('maxChars')
        if hi is None:
            return copy, hashtags
        n = len(copy)
        if n <= hi and (lo is None or n >= lo):
            return copy, hashtags
        if lo is not None and n < lo:
            note = f'Your previous attempt was only {n} characters — too short. This format requires {lo}-{hi} characters; add more relevant detail or context (do not invent facts) to reach at least {lo}.'
        else:
            note = f'Your previous attempt was {n} characters — too long. This format requires at most {hi} characters; tighten it without dropping the key facts.'
        try:
            result = safe_call(f'{extra}\nIMPORTANT: {note}'.strip())
        except ValueError:
            # Couldn't get a usable re-roll — keep the original draft rather than losing the variant.
            return copy, hashtags
        copy     = clean_emojis(result.get('copy', copy), platform)
        hashtags = result.get('hashtags', hashtags)
        if len(copy) > hi:
            copy = smart_truncate(copy, hi)
        return copy, hashtags

    variants = []
    if angles:
        # Each angle is a distinct, intentional framing — generate exactly one variant per angle.
        for angle in angles:
            try:
                result   = safe_call(angle['instruction'])
                copy     = clean_emojis(result.get('copy', ''), platform)
                hashtags = result.get('hashtags', [])
                copy, hashtags = _enforce_length(copy, hashtags, angle['instruction'])
            except ValueError as e:
                # This one angle never produced a usable response — skip it rather than
                # failing the whole request (the user would otherwise see nothing generated).
                print(f'[copy/generate] dropped {platform}/{angle["label"]} variant: {e}', file=sys.stderr)
                continue
            variants.append({'copy': copy, 'hashtags': hashtags, 'label': angle['label']})

        if not variants:
            raise ValueError(f'{platform} copy generation failed for all variants — try again')
    else:
        for i in range(variant_count):
            result   = call()
            copy     = clean_emojis(result.get('copy', ''), platform)
            hashtags = result.get('hashtags', [])
            variants.append({'copy': copy, 'hashtags': hashtags})

    primary = variants[0]
    return {
        'variants': variants,
        'copy': primary['copy'],
        'hashtags': primary['hashtags'],
        'charCount': len(primary['copy']),
        'platform': platform,
    }


def handle_generate_image(body):
    article   = body.get('article', {})
    platform  = body.get('platform', 'X')
    media     = body.get('mediaBrand', 'ChainReporter')
    sentiment = body.get('sentiment', 'Neutral')
    model     = body.get('model', 'openai/gpt-5.4-image-2')

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

    image_b64 = openrouter_image(prompt, model)
    return {'imageB64': image_b64, 'prompt': prompt, 'model': model}


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


# ── OpenRouter helper (uses openai SDK for robust threading/chunked support) ───
import openai as _openai_sdk

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


def handle_editorial_select(body):
    """Generator — yields (model_key, result_dict) as each model finishes.

    Validation (ValueError) happens before the first yield, so callers can
    pull `next(gen)` to surface a clean 400 before committing to a streamed
    response (HTTP headers can't be unsent once writing begins).
    """
    shortlist      = body.get('shortlist', [])
    sel_media      = body.get('selectedMedia', [])
    sel_plats      = body.get('selectedPlatforms', ['X', 'Telegram', 'Instagram'])
    topics         = body.get('topics', '').strip()
    test_mode      = body.get('testMode', False)

    if not shortlist:
        raise ValueError('shortlist is empty')
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')

    if test_mode:
        brand_list = ', '.join(f'"{m}"' for m in sel_media)
        lines = '\n'.join(
            f'[{a["input_index"]}] {a.get("title","")} — {a.get("source","")}'
            for a in shortlist
        )
        system_prompt = (
            'You are a test assistant. Rewrite each article in very short format and return ONLY valid JSON.\n'
            f'Brands: [{brand_list}]. For each brand pick 1 article and rewrite it very briefly.\n'
            'Schema: {"brands":{"<brand>":[{"input_index":<N>,"platform":"X","title":"<short title>",'
            '"source":"<src>","source_url":"#","selection_reason":"test","copy":"<one sentence>",'
            '"hashtags":["#Test"],"suitability_score":80,"impact_score":80,"virality_score":80,"confidence_score":80}]}}'
        )
        user_prompt = f'Articles:\n{lines}'
        sel_models  = body.get('selectedModels', list(EDITORIAL_MODELS.keys()))
        active_models = {k: v for k, v in EDITORIAL_MODELS.items() if k in sel_models}
        from concurrent.futures import ThreadPoolExecutor, as_completed
        # Thinking models (Gemini 2.5 Pro, etc.) consume tokens on internal reasoning
        # before generating output, so they need a higher cap even in test mode.
        THINKING_MODELS = {'gemini'}
        with ThreadPoolExecutor(max_workers=len(active_models)) as pool:
            futures = {
                pool.submit(_editorial_call_one, k, {**v, 'max_tokens': 4000 if k in THINKING_MODELS else 800}, system_prompt, user_prompt): k
                for k, v in active_models.items()
            }
            for fut in as_completed(futures):
                yield fut.result()
        return

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
    with ThreadPoolExecutor(max_workers=len(active_models)) as pool:
        futures = {
            pool.submit(_editorial_call_one, k, v, system_prompt, user_prompt): k
            for k, v in active_models.items()
        }
        for fut in as_completed(futures):
            yield fut.result()


# ── Embedding filter pipeline handler ──────────────────────────────────────────
def handle_filter_pipeline(body):
    if not _FILTERING_AVAILABLE:
        raise ValueError('filtering package not installed (pip install numpy)')
    articles       = body.get('articles', [])
    selected_media = body.get('selectedMedia', [])
    topics         = body.get('topics', '')
    recency_hours  = int(body.get('recencyHours', 24))
    if not articles:
        raise ValueError('articles array is empty')
    if not selected_media:
        raise ValueError('selectedMedia is empty')
    return _run_pipeline(articles, selected_media, topics, recency_hours)


def handle_deepseek_filter(body):
    if not _DEEPSEEK_FILTER_AVAILABLE:
        raise ValueError('deepseek_pipeline not available')
    articles       = body.get('articles', [])
    selected_media = body.get('selectedMedia', [])
    topics         = body.get('topics', '')
    recency_hours  = int(body.get('recencyHours', 24))
    if not articles:
        raise ValueError('articles array is empty')
    if not selected_media:
        raise ValueError('selectedMedia is empty')
    return _run_deepseek_pipeline(
        articles, selected_media, topics, recency_hours,
        _openrouter_chat=openrouter_chat,
        _repair_json=_repair_json,
    )


# ── HTTP Request Handler ───────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        # self.command/self.path may be unset if the request line itself failed
        # to parse (malformed/truncated request) — send_error() still logs in
        # that case, so guard with getattr to avoid crashing the handler thread.
        cmd  = getattr(self, 'command', '?')
        path = getattr(self, 'path', '?')
        print(f'[{cmd}] {path} — {args[1] if len(args) > 1 else ""}')

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', ORIGIN)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self._json({'ok': True})
        elif self.path.startswith('/api/rss'):
            from urllib.parse import urlparse, parse_qs, unquote
            params = parse_qs(urlparse(self.path).query)
            url    = unquote(params.get('url', [''])[0])
            if not url:
                return self._error(400, 'url parameter required')
            try:
                r = requests.get(url, timeout=15,
                                 headers={'User-Agent': 'Mozilla/5.0 (compatible; ChainReporter/1.0)'})
                r.raise_for_status()
                body = r.content
                self.send_response(200)
                self.send_cors()
                self.send_header('Content-Type', r.headers.get('Content-Type', 'application/xml'))
                accepts_gzip = 'gzip' in self.headers.get('Accept-Encoding', '')
                if accepts_gzip and len(body) > 1024:
                    body = gzip.compress(body)
                    self.send_header('Content-Encoding', 'gzip')
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self._error(502, f'RSS fetch failed: {e}')
        else:
            self._error(404, 'Not found')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        raw    = self.rfile.read(length)
        if 'gzip' in self.headers.get('Content-Encoding', ''):
            try:
                raw = gzip.decompress(raw)
            except OSError:
                return self._error(400, 'Invalid request encoding')
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return self._error(400, 'Invalid JSON')

        try:
            path = self.path.rstrip('/')
            if path == '/api/copy/generate':
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
                gen = handle_editorial_select(body)
                first = next(gen)   # raises ValueError before any header is sent
                try:
                    self._stream_ndjson_start()
                    self._stream_ndjson_write({first[0]: first[1]})
                    for key, data in gen:
                        self._stream_ndjson_write({key: data})
                    self._stream_ndjson_end()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass   # client disconnected mid-stream — headers already sent, nothing more to do
                except Exception as e:
                    print(f'[ERROR] editorial-select stream: {e}', file=sys.stderr)
                return
            elif path == '/api/filter/pipeline':
                self._json(handle_filter_pipeline(body))
            elif path == '/api/filter/deepseek':
                self._json(handle_deepseek_filter(body))
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
        body = json.dumps(data, default=_json_default).encode()
        self.send_response(status)
        self.send_cors()
        self.send_header('Content-Type', 'application/json')
        # Large AI responses (100s of KB) can stall mid-transfer on networks with
        # MTU/PMTUD issues (VPNs, mobile, some ISPs). Gzip shrinks JSON ~70-85%,
        # which both speeds delivery and avoids tripping that black hole.
        accepts_gzip = 'gzip' in self.headers.get('Accept-Encoding', '')
        if accepts_gzip and len(body) > 1024:
            body = gzip.compress(body)
            self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        self._json({'error': msg}, code)

    def _stream_ndjson_start(self):
        self.send_response(200)
        self.send_cors()
        self.send_header('Content-Type', 'application/x-ndjson')
        self.send_header('Transfer-Encoding', 'chunked')
        self.end_headers()

    def _stream_ndjson_write(self, obj):
        line  = (json.dumps(obj, default=_json_default) + '\n').encode()
        chunk = f'{len(line):x}\r\n'.encode() + line + b'\r\n'
        self.wfile.write(chunk)
        self.wfile.flush()

    def _stream_ndjson_end(self):
        self.wfile.write(b'0\r\n\r\n')
        self.wfile.flush()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not OPENROUTER_KEY:
        print('[WARN] OPENROUTER_API_KEY not set — AI routes will fail', file=sys.stderr)
    if not SCRIPT_URL or SCRIPT_URL.startswith('PASTE_'):
        print('[WARN] GOOGLE_APPS_SCRIPT_URL not set — Sheets routes will fail', file=sys.stderr)

    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    server.daemon_threads = True
    print(f'ChainReporter backend running at http://localhost:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
