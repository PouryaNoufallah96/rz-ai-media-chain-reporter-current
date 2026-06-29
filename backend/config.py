"""
Central configuration & shared constants for the ChainReporter backend.
All env-derived settings and the small platform/model lookup dicts live here
so every other module can `from config import *` (or named imports).
"""
import os
import re
from pathlib import Path
from datetime import datetime as _datetime, date as _date, timedelta as _timedelta, timezone as _timezone

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
COOKIE_SECURE   = os.environ.get('COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')

# Keep in sync with frontend/src/store/mmStore.js MEDIA_LIST
MEDIA_LIST = ['RZ Prime', 'Coin Hall', 'ChainReporter', 'Meta Coin Guard']
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
            'STRUCTURE: a bold headline line, then a short body that covers what happened and why it matters, then 3-5 hashtags at the end.\n'
            'HARD RULE: response must be 300-600 characters total, including spaces, line breaks, emoji and hashtags.\n'
            'HARD RULE: do NOT include any "Source:", "Subject:", "Flag:", "Caveat:" or any "📌 Label: value" labeled bullets — no attribution lines of any kind.\n'
            'EMOJI POLICY: sparing and structural — 📌 for bullets only if the angle calls for it, 🚨 only for breaking news, nothing decorative.\n'
            f'Suggested topic→emoji anchors (use only if relevant, never force them): {_EMOJI_HINT}.\n'
            f'{_FACT_RULE}\n'
            'End with 3-5 hashtags on the last line.\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }'
            + _sibling_block(sibling_copy, 'X')
        ),
        'variant_angles': [
            {'label': 'Viral',        'instruction': 'ANGLE: write this to go viral — bold provocative headline that stops the scroll, then 1-2 sentences that build tension or surprise, a short punchy closing line that makes people want to share or comment. Tone: energetic, opinionated, slightly dramatic but fact-grounded. No labeled bullets, no source line.'},
            {'label': 'Analysis',     'instruction': 'ANGLE: critical analyst voice — go beyond the headline, explain the deeper implications, challenge the obvious reading, or frame what most people are missing. Tone: sharp, skeptical, intellectually honest. No labeled bullets, no source line.'},
            {'label': 'To the point', 'instruction': 'ANGLE: maximum brevity — one bold headline, then 2-3 tight sentences that say exactly what happened and why it matters, nothing else. No bullet points, no labeled fields, no source line. Aim for the lower end of the character range.'},
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

# ── Per-brand identity hashtag, always prepended to generated copy hashtags ──
BRAND_HASHTAGS = {
    'RZ Prime':        '#RZPrime',
    'Coin Hall':       '#CoinHall',
    'Meta Coin Guard': '#MetaCoinGuard',
    'ChainReporter':   '#ChainReporter',
}

# ── Promotional copy: per-brand product pitch injected when promoMode=True ────
BRAND_PROMO_PITCH = {
    'RZ Prime': (
        "RZ Prime is a token-reservation platform: reserve token deals with zero upfront payment, "
        "keep your funds unlocked, pay only if the price rises, cancel anytime with no penalties — "
        "all enforced on-chain by smart contracts."
    ),
    'Coin Hall': (
        "Coin Hall is a tokenized real-world-asset deal platform — users reserve time-limited deals "
        "on tokenized assets (jewelry, real estate, cars), each with a set quantity and end date that "
        "resolves as Win or Lose, with full outcome history tracked on-chain."
    ),
    'Meta Coin Guard': (
        "Meta Coin Guard is an automated on-chain protection service for crypto token value: connect "
        "your wallet, choose a cover plan, and smart contracts automatically compensate you in RZ USD "
        "if your tokens lose value — non-custodial, no KYC, no claims process, no intermediary. "
        "Built for large holders, funds, and treasury managers."
    ),
}

# ── OpenRouter image generation model modalities ──────────────────────────────
OPENROUTER_IMAGE_MODELS = {
    'google/gemini-3.1-flash-image-preview':['image', 'text'],
    'google/gemini-3-pro-image-preview':    ['image', 'text'],
    'openai/gpt-5.4-image-2':              ['image', 'text'],
    'recraft/recraft-v4-pro':              ['image'],
}

# ── Art Director tunables (used by image_pipeline) ────────────────────────────
ART_DIRECTOR_TEMPERATURE = 0.95
ART_DIRECTOR_MAX_TOKENS = 900

_CORE_AXES = ('environment', 'camera', 'energy', 'mood_accent')

# ── Brief validation guardrails (used by image_pipeline) ──────────────────────
_BANNED_SUBJECT_TERMS = ['text', 'label', 'logo', 'watermark', 'rz prime', 'chainreporter', 'coin hall', 'meta coin guard']
_WALLET_ADDRESS_RE = re.compile(r'0x[a-fA-F0-9]{6,}')

# ── Activity batching window (used by handlers.account) ───────────────────────
BATCH_WINDOW = _timedelta(minutes=10)
VALID_ACTIONS = {'approved', 'scheduled'}

# ── Background scheduler ──────────────────────────────────────────────────────
SCHEDULER_INTERVAL_SEC = 30
