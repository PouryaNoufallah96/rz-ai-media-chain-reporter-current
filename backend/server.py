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
from datetime import datetime as _datetime, date as _date, timedelta as _timedelta, timezone as _timezone

import auth
import database

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


# ── ISO timestamp normalization (frontend Date.toISOString() → _now_iso() shape) ─
def _parse_iso_utc(s):
    s = s.strip()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    if '.' in s:
        head, rest = s.split('.', 1)
        for i, ch in enumerate(rest):
            if ch in '+-':
                frac, offset = rest[:i], rest[i:]
                break
        else:
            frac, offset = rest, ''
        s = f'{head}.{(frac + "000000")[:6]}{offset}'
    dt = _datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_timezone.utc)
    return dt.astimezone(_timezone.utc)


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

# ── Per-brand image generation profiles (Art Director -> deterministic Assembler) ──
# Each profile is the "contract" for the two-stage image pipeline:
#   Stage 1 (Art Director LLM)   — outputs a JSON visual brief (see _build_art_director_system_prompt)
#   Stage 2 (assemble_prompt)    — deterministically merges the brief with the frozen style below
# Brands without a profile here fall back to the legacy BRAND_VISUAL_TONE prompt in handle_generate_image.
BRAND_IMAGE_PROFILES = {
    'RZ Prime': {
        'brand_name': 'RZ Prime',
        'brand_tagline': (
            'a premium crypto/Web3 reservation-protocol brand: clean product-visualization 3D, '
            'glass UI panels on circuit-board platforms, educational comparisons, and two recurring '
            'mascot characters (Blue Kid and Wolf)'
        ),
        'headline_max_words': 10,
        'headline_uppercase': True,
        'mood_accent_default': 'cyan',
        'mood_accent_restricted': {
            'cyan_vs_red':   {'families': ['versus', 'shatter', 'table']},
            'cyan_vs_green': {'families': ['versus', 'product', 'table', 'data_tiles']},
        },
        'axis_optional':          {'wolf': True},
        'axis_inject_after_data': ['wolf'],
        'passthrough_fields':     ['read'],
        'brief_prefix_schema':    {'read': 'CONTRAST | NUMBER | PROCESS | THREAT | LAUNCH | EDUCATION'},
        'brand_keywords': ['rz prime', 'rzprime'],
        'logo_line': (
            "In the bottom-left corner of the frame, include the RZ Prime wordmark: "
            "'RZ' in heavy bold above 'Prime' in light weight, both white and small. "
            "A small green 'RZ' coin icon may appear beside it. "
            "This is the ONLY brand logo permitted in the frame."
        ),
        'wolf_descriptions': {
            'none':    'no mascot characters in the scene (default when the layout is already visually complex)',
            'kid':     ('the Blue Kid mascot stands in the scene -- a round-faced child character with electric-blue '
                        'hair, an orange-brown fuzzy beanie hat, an oversized fuzzy blue sweater, dark shorts, and '
                        'bright green sneakers -- pointing at, touching, or presenting a glass UI panel'),
            'wolfman': ('the Wolf mascot stands in the scene -- a low-poly faceted blue wolf at human height, wearing '
                        'a tailored dark business suit with white shirt and tie -- gesturing toward or presenting '
                        'information on a glass panel'),
            'both':    ('both mascot characters appear together in the scene: the Blue Kid (round-faced child with '
                        'blue hair, orange beanie, oversized fuzzy blue sweater, dark shorts, green sneakers) and '
                        'the Wolf (low-poly faceted blue wolf in a dark suit with white shirt and tie) -- they flank '
                        'or interact with glass UI panels, pointing and presenting'),
        },
        'data_element_template': 'a clear glass UI panel displaying the value "{value}"{label_part}',
        'data_element_label_template': ' with the label "{label}"',
        'legibility_line': "All in-scene text is large, bold, crisp and clearly legible, each rendered on its own clear glass panel or surface.",
        'anti_repetition_rules': (
            "Hard rules: do not pick the same family 3 times in a row; do not use the "
            "'circuit_floor' environment more than 4 times in a row (it is the dominant default but still "
            "needs occasional variation); vary the wolf/character value -- do not use the same value twice "
            "in a row; use 'both' at most once every 4 posts; rotate camera and energy so consecutive "
            "posts don't feel identical."
        ),
        'frozen_style': {
            'format': "vertical 4:5 editorial poster, 1080x1350",
            'palette': (
                "near-black deep-navy base (#05080F-#0A1422) -- the background is genuinely dark in EVERY frame. "
                "Electric cyan/teal is the primary neon accent (#1FE0C2-#2FF0E0). Bright emerald green (#2BE38A) "
                "marks the positive/RZ Prime side (checkmarks, up-arrows, the Reserve action, the 'RZ Prime' label). "
                "Alarm red (#FF3B3B) marks the negative/legacy side (X marks, down-arrows, broken systems). "
                "Amber-orange (#FF8A3C) is reserved for caution cards and the Blue Kid's beanie hat. "
                "Soft violet-purple (#7A5BFF) is a SECONDARY glow only (rim light, atmosphere) and never leads. "
                "Typography is white, bold, UPPERCASE."
            ),
            'materials': (
                "clear glass UI panels and app-mockup screens (NOT frosted glassmorphism) with glowing cyan edges; "
                "circuit-board floor platform with illuminated trace lines; dark reflective surfaces; "
                "semi-transparent glass cubes and structures with visible internals; holographic accents."
            ),
            'rendering': (
                "clean product-visualization 3D, closer to a polished app-mockup render than a heavy octane-render "
                "scene. Still cinematic with volumetric light rays, soft fog, and floating particles, but more "
                "accessible and readable than hyper-detailed CG. Glow is the primary light source. No daylight. "
                "Two recurring mascot characters may appear across any family: "
                "(1) 'Blue Kid' -- a 3D character with a round face, simple features, electric-blue hair, an "
                "orange-brown fuzzy beanie hat, an oversized fuzzy blue sweater, dark shorts, and bright green "
                "sneakers; rendered with soft materials, NOT low-poly. "
                "(2) 'Wolf' -- a low-poly faceted blue wolf at human height, wearing a tailored dark business suit "
                "with a white shirt and tie; rendered in ice-blue and navy triangular planes. "
                "They interact with UI panels -- pointing, presenting, standing beside displays."
            ),
            'background_vocab': (
                "circuit-board floor with glowing cyan trace lines is THE dominant backdrop, appearing in the "
                "majority of images. Server corridor with perspective lines is the secondary environment. "
                "Network nodes and constellation-like connections fill deep backgrounds. Dark void with subtle "
                "tech elements for minimal scenes."
            ),
            'headline_zone': (
                "the top 25-35% of the frame is reserved for the headline; the headline is large, bold, "
                "UPPERCASE, white sans-serif. One key word MAY be solid cyan or green. Headlines are often "
                "conversational questions or provocative statements, 8-10 words."
            ),
            'never': (
                "no photorealistic humans (only the Blue Kid and Wolf mascot characters described above); "
                "no frosted or blurred glassmorphism (glass is always CLEAR); "
                "no daylight or outdoor photography; no white, pastel, or light-blue backgrounds; "
                "no stock-photo look; no flat 2D illustration; no real third-party logos or branded coins "
                "(competitors appear only as abstract glass tokens); no wallet addresses (0x...); "
                "no tiny labels or micro-text."
            ),
        },
        'metaphors': {
            "blockchain / smart contracts":   "clear glass cubes with glowing edges and visible circuit internals",
            "UI / interface / data":          "glass app-mockup panels and screens on pedestals",
            "security / verification":        "glowing green checkmarks, VERIFIED / AUDITED / ON-CHAIN badges on glass panels",
            "legacy finance / old model":     "dim greyscale elements, crumbling structures, X marks in red, broken screens",
            "tokens / capital / reserve":     "glass coins, the green RZ coin icon, streams of light",
            "network / market":               "constellation-like nodes connected by glowing lines",
            "risk / failure":                 "cracked glass with red glow and shattering fragments",
            "comparison / choices":           "left/right split frame with red (bad) vs cyan-green (good) sides",
            "process / flow":                 "connected glass panels with directional arrows between stages",
            "countdown / expiry":             "digital countdown display on a glass panel, timer UI elements",
        },
        'families': {
            'versus': {
                'name': "VERSUS / SPLIT",
                'skeleton': (
                    "The frame is divided left/right. The negative side glows dim alarm red with X marks, "
                    "down-arrows, broken or crumbling elements representing legacy finance, middlemen, or a "
                    "flawed system -- optionally shown as a failing UI screen. The positive side is ordered, "
                    "pristine, glowing cyan-green glass with checkmarks, up-arrows, and the RZ Prime answer. "
                    "Glass UI panels on each side may carry comparison labels. The Blue Kid and/or Wolf mascots "
                    "may stand on the positive side, presenting or gesturing toward the RZ panels."
                ),
                'text_policy': (
                    "Headline plus up to 6 short labels or phrases across both sides (large, on glass surfaces). "
                    "Each side may carry 2-3 labels identifying what it represents. Labels on the negative side "
                    "may be struck-through or dimmed. Full short sentences on panels are permitted."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'dramatic_tension'},
                'data_budget': 6,
            },
            'product': {
                'name': "PRODUCT SHOWCASE",
                'skeleton': (
                    "A central glass UI panel or app-mockup screen sits on a circuit-board platform, showcasing "
                    "the RZ Prime interface, a reserve mechanism, or a protocol concept. The panel looks like an "
                    "actual app screen with fields, buttons, and status indicators rendered in glass. Supporting "
                    "elements (smaller panels, glass cubes, coin icons) may orbit at the edges. The Blue Kid "
                    "and/or Wolf may stand beside the central panel, presenting it."
                ),
                'text_policy': (
                    "Headline plus up to 4 UI labels or values on the central panel (e.g. 'RESERVE $500', "
                    "'RZUSD', 'AVAILABLE', status fields). These are part of the UI mockup, not floating labels. "
                    "Keep each label to 1-4 words."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'low_angle_hero', 'energy': 'calm_premium'},
                'data_budget': 4,
            },
            'flow': {
                'name': "FLOW / DECISION TREE",
                'skeleton': (
                    "A sequence of 3-5 connected glass panels or steps showing a process, decision tree, or "
                    "user journey. Glowing arrows or light paths connect the stages. The flow may branch into "
                    "two outcome panels at the bottom (e.g. 'Pay' vs 'Walk Away'). Panels sit on a circuit-board "
                    "platform or float in a structured arrangement. The Blue Kid and/or Wolf may stand at the "
                    "start or end of the flow, or beside a key decision point."
                ),
                'text_policy': (
                    "Headline plus up to 5 short phrases (1-5 words each) written large on the connected panels. "
                    "Each panel carries one step or outcome label. Weave the phrases directly into the scene "
                    "description. Full short sentences are permitted on panels."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'calm_premium'},
                'data_budget': 5,
            },
            'table': {
                'name': "COMPARISON TABLE",
                'skeleton': (
                    "A glass comparison panel fills the center of the frame on a circuit-board platform: a "
                    "feature column on the left, one or two comparison columns (e.g. 'OLD MODEL' dim/red, "
                    "'RZ PRIME' glowing cyan-green). Each row is a clear glass shelf with crisp large text. "
                    "Alternatively, a 'Myth vs Reality' format with two columns. The Blue Kid and/or Wolf "
                    "may flank the table, gesturing toward key rows."
                ),
                'text_policy': (
                    "Headline plus up to 8 row labels (1-4 words each) inside the table, plus column headers. "
                    "Tables can be text-heavy -- this is intentional. Column headers and row labels count toward "
                    "the budget. Each cell is large and legible on its own glass surface."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'calm_premium'},
                'data_budget': 8,
            },
            'character': {
                'name': "CHARACTER SCENE",
                'skeleton': (
                    "The Blue Kid and/or Wolf mascots are the heroes of the scene, prominently placed and "
                    "interacting with glass UI panels, countdown timers, verification badges, or data displays. "
                    "The characters may be pointing at panels, touching interfaces, looking at verification "
                    "results, or standing together flanking a central display. Glass speech-bubble panels may "
                    "float near them. The setting is a circuit-board platform with the characters at roughly "
                    "center-frame."
                ),
                'text_policy': (
                    "Headline plus up to 4 in-scene text elements: speech bubbles (5 words or fewer each), "
                    "UI panel labels (1-4 words), or badge text (VERIFIED, ON-CHAIN, etc.). The characters and "
                    "their interaction with the panels tell the story."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'calm_premium'},
                'data_budget': 4,
            },
            'shatter': {
                'name': "SHATTER / DISRUPT",
                'skeleton': (
                    "A pristine central RZ glass object (cube, shield, or smart-contract panel) stands intact "
                    "and luminous, bearing VERIFIED / AUDITED / ON-CHAIN badges in green. At the edges of the "
                    "frame, legacy elements labeled CUSTODY, MIDDLEMAN, BUREAUCRACY shatter outward in "
                    "slow-motion fragments with red X marks, alarm-red cracks radiating from impact points. "
                    "The circuit-board floor anchors the central object."
                ),
                'text_policy': (
                    "Headline plus up to 5 labels: 2-3 on the central intact object (VERIFIED, AUDITED, "
                    "ON-CHAIN, 1-2 words each, green-tinted) and 2-3 shattering labels at the edges "
                    "(CUSTODY, MIDDLEMAN, etc., 1-2 words each, red-tinted with X marks)."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'low_angle_hero', 'energy': 'explosive_dynamic'},
                'data_budget': 5,
            },
            'data_tiles': {
                'name': "DATA TILES / CARDS",
                'skeleton': (
                    "2-3 ascending glass tiles, cards, or phone-screen mockups sit on a circuit-board platform, "
                    "each carrying ONE large value and ONE short label. They may be arranged as ascending stairs "
                    "to convey growth, or as side-by-side comparison cards (e.g. 'Traditional Market' red vs "
                    "'RZ Prime' cyan). A relevant hero element (coin icon, chart silhouette) may float above."
                ),
                'text_policy': (
                    "Headline plus a maximum of 3 data elements. Each value is 1-5 characters (e.g. 3%, 6%, 9%), "
                    "each label is 1-3 words. Values are rendered larger than labels. Cards may have a colored "
                    "accent edge (red for negative comparison, cyan/green for RZ)."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'low_angle_hero', 'energy': 'calm_premium'},
                'data_budget': 3,
            },
            'blueprint': {
                'name': "BLUEPRINT / ARCHITECTURE",
                'skeleton': (
                    "A technical architecture view: a glass desk or platform with floating holographic panels "
                    "showing a system diagram, smart contract structure, or protocol architecture. Elements "
                    "may include a Smart Contract file panel, a magnifying glass over code, an on-chain explorer "
                    "window, blockchain cubes, or a schematic wall with connecting lines. The Wolf may stand "
                    "inside a glass cube or beside the architecture. Legacy elements (dim, warm) may contrast "
                    "with on-chain elements (bright, cyan) to show transformation."
                ),
                'text_policy': (
                    "Headline plus up to 4 short labels on panels or elements (e.g. 'Smart Contract', "
                    "'On-Chain Explorer', 'VERIFIED', 'Legacy Rails'). The architecture diagram itself "
                    "may contain abstract connecting lines and icons."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'calm_premium'},
                'data_budget': 4,
            },
        },
        'axes': {
            'environment': {
                'circuit_floor':    ("The setting is a dark reflective circuit-board floor with glowing cyan trace "
                                     "lines radiating outward beneath the main subject, the brand's signature platform."),
                'server_corridor':  ("The setting is a neon-lit futuristic corridor with strong perspective lines "
                                     "converging toward a glowing vanishing point."),
                'deep_network':     ("The setting is a deep dark void filled with faint network nodes and "
                                     "constellation-like connections, a vast digital space."),
                'glass_chamber':    ("The setting is an enclosed glass chamber with translucent walls showing "
                                     "circuit patterns, a controlled tech environment."),
            },
            'camera': {
                'eye_level_symmetric': ("The camera is at eye level, centered symmetrically, giving a balanced "
                                        "architectural view of the scene."),
                'low_angle_hero':      ("The camera looks up at the scene from a low angle, making the central "
                                        "subject feel monumental."),
                'one_point_corridor':  ("The camera is positioned frontally with one-point perspective, pulling "
                                        "the eye straight down the depth of the scene."),
                'slight_overhead':     ("The camera looks down at a slight overhead angle, giving a clear view "
                                        "of panels and platform layout."),
            },
            'energy': {
                'calm_premium':      "The lighting is still and confident, with a soft, even glow throughout the scene.",
                'dramatic_tension':  ("The lighting is high-contrast with deep shadows and drifting fog, creating "
                                      "dramatic tension."),
                'explosive_dynamic': ("The scene is full of motion, with fragments hanging mid-air and bursts of "
                                      "light radiating outward, conveying explosive energy."),
            },
            'mood_accent': {
                'cyan':          "The dominant accent color throughout the scene is electric cyan/teal.",
                'cyan_vs_red':   ("The scene contrasts electric cyan/green on the positive side against "
                                  "dim alarm red on the negative side."),
                'cyan_vs_green': ("The scene features both electric cyan/teal for analytical elements and "
                                  "bright emerald green for active/positive/RZ elements."),
            },
            'wolf': {
                'none':    '',
                'kid':     ("The Blue Kid mascot stands in the scene -- a round-faced 3D character with electric-blue "
                            "hair, an orange-brown fuzzy beanie hat, an oversized fuzzy blue sweater, dark shorts, and "
                            "bright green sneakers -- pointing at or interacting with a glass UI panel."),
                'wolfman': ("The Wolf mascot stands in the scene -- a low-poly faceted blue wolf at human height, "
                            "wearing a tailored dark business suit with white shirt and tie -- gesturing toward or "
                            "presenting information on a glass panel."),
                'both':    ("Both mascot characters appear together: the Blue Kid (round-faced, blue hair, orange "
                            "beanie, fuzzy blue sweater, dark shorts, green sneakers) and the Wolf (low-poly faceted "
                            "blue wolf in a dark suit with white shirt and tie) -- flanking or interacting with glass "
                            "UI panels, pointing and presenting."),
            },
        },
        'routing_table': """
Classify the article's sharpest claim as one READ, then pick the family:

CONTRAST (A vs B, custody vs on-chain, with/without RZ, fee comparison, old vs new model)
  general contrast / two sides ........ versus        (fallback: table)
  explicit feature-by-feature ......... table         (fallback: versus)
  myths vs reality / fact-check ....... table         (fallback: versus)

NUMBER (stat, price, record, fee structure, metric comparison)
  ascending metrics / fee tiers ....... data_tiles    (fallback: product)
  product screen IS the proof ......... product       (fallback: data_tiles)

PROCESS (how-it-works, lifecycle, expiry, reservation mechanism, decision tree)
  ordered steps / user journey ........ flow          (fallback: product)
  conditional / what-if outcomes ...... flow          (fallback: versus)

THREAT (regulation, crackdown, hack, scam, trust, verification)
  regulation / compliance positive .... shatter       (fallback: blueprint)
  scam / trust / verification ......... shatter       (fallback: versus)
  legacy-to-onchain transition ........ blueprint     (fallback: shatter)

LAUNCH (product feature, protocol update, new capability)
  product / interface showcase ........ product       (fallback: data_tiles)
  architecture / infrastructure ....... blueprint     (fallback: product)

EDUCATION (explainer, guide, FAQ, newcomer onboarding)
  how-it-works / newcomer guide ....... flow          (fallback: product)
  architecture / audit / infra ........ blueprint     (fallback: flow)
  character-led explanation ........... character     (fallback: flow)

Anything ambiguous .................... product       (fallback: versus)
""".strip(),
        'text_rules': """
1. Headline: 10 words or fewer, UPPERCASE, punchy and often a conversational question or provocative
   statement. Big numbers and tickers are encouraged. One key word MAY be solid cyan or green.
   Never use hard-to-spell proper nouns -- tickers (BTC, ETH, RZUSD) are fine.
2. In-scene text budget per family: versus up to 6 labels across both sides, product up to 4 UI labels,
   flow up to 5 step/outcome phrases, table up to 8 row labels plus headers, character up to 4
   (speech bubbles + panel labels), shatter up to 5 (center badges + edge labels), data_tiles up to 3
   value+label pairs, blueprint up to 4 panel labels.
3. Every in-scene text string must sit on its own clear glass panel or surface.
4. Values are 1-5 characters; labels and phrases are 1-5 words; render them large and crisp.
5. UI labels like RESERVED, AVAILABLE, VERIFIED, AUDITED, ON-CHAIN are encouraged where relevant.
6. Full short sentences on glass panels are permitted (up to 8 words) -- this brand is text-heavy
   by design. Speech bubbles may carry conversational phrases.
7. No real company/exchange names anywhere in the image. No wallet addresses (0x...).
""".strip(),
        'fallback_brief': {
            'read': 'LAUNCH',
            'family': 'product',
            'headline': 'CRYPTO MARKETS MOVE',
            'data_elements': [],
            'environment': 'circuit_floor',
            'camera': 'eye_level_symmetric',
            'energy': 'calm_premium',
            'mood_accent': 'cyan',
            'wolf': 'none',
            'subject_scene': (
                "A single clear glass UI panel sits on a dark circuit-board platform with glowing cyan "
                "trace lines, displaying a clean app-mockup interface with a status indicator and the "
                "green RZ coin icon, radiating soft cyan light."
            ),
        },
        'brief_examples': """
Worked examples (for guidance only -- do not copy headlines or scenes verbatim):

A. Article: "Why custodial exchanges still hold your crypto hostage"
{"read": "CONTRAST", "family": "versus", "headline": "NOT YOUR KEYS, NOT YOUR CRYPTO", "data_elements": [{"value": "CUSTODY", "label": ""}, {"value": "ON-CHAIN", "label": ""}, {"value": "MIDDLEMAN", "label": ""}, {"value": "DIRECT", "label": ""}], "environment": "circuit_floor", "camera": "eye_level_symmetric", "energy": "dramatic_tension", "mood_accent": "cyan_vs_red", "wolf": "both", "subject_scene": "On the left, a dim red-tinted panel shows CUSTODY and MIDDLEMAN with red X marks, broken glass fragments drifting from it. On the right, a pristine cyan-green panel shows ON-CHAIN and DIRECT with green checkmarks. The Blue Kid and Wolf stand on the right side, the Kid pointing at the positive panel while the Wolf gestures dismissively at the broken left side. Circuit-board floor with glowing traces beneath."}

B. Article: "RZ Prime launches structured early access for token reservations"
{"read": "LAUNCH", "family": "product", "headline": "EARLY ACCESS SHOULD BE STRUCTURED", "data_elements": [{"value": "RESERVE", "label": ""}, {"value": "RZUSD", "label": ""}, {"value": "AVAILABLE", "label": ""}], "environment": "circuit_floor", "camera": "low_angle_hero", "energy": "calm_premium", "mood_accent": "cyan_vs_green", "wolf": "none", "subject_scene": "A large clear glass UI panel sits on a circuit-board platform, displaying an app-mockup reserve interface with RESERVE, RZUSD, and AVAILABLE fields glowing in cyan and green, the green RZ coin icon hovering beside it."}

C. Article: "What actually happens when your reservation window expires"
{"read": "PROCESS", "family": "flow", "headline": "WHAT ACTUALLY HAPPENS IF I DO NOTHING", "data_elements": [{"value": "EXPIRES", "label": "WINDOW"}, {"value": "RELEASED", "label": "TOKENS"}, {"value": "$0", "label": "COST"}], "environment": "circuit_floor", "camera": "eye_level_symmetric", "energy": "calm_premium", "mood_accent": "cyan", "wolf": "both", "subject_scene": "Three connected clear glass panels descend diagonally on a circuit-board platform, arrows linking them: WINDOW EXPIRES at top, TOKENS RELEASED in middle, YOU PAY ZERO at bottom with a green checkmark. The Blue Kid touches the top panel while the Wolf stands at the bottom, gesturing calmly toward the zero-cost outcome."}

D. Article: "The old model vs RZ Prime: a feature comparison"
{"read": "CONTRAST", "family": "table", "headline": "WHY ARE PEOPLE STILL USING THE OLD MODEL", "data_elements": [{"value": "CeFi", "label": ""}, {"value": "RZ", "label": ""}, {"value": "FEES", "label": ""}, {"value": "KYC", "label": ""}, {"value": "CUSTODY", "label": ""}], "environment": "circuit_floor", "camera": "slight_overhead", "energy": "calm_premium", "mood_accent": "cyan_vs_red", "wolf": "kid", "subject_scene": "A glass comparison table fills the center on a circuit-board platform: CeFi column dim and red-tinted on the left, RZ PRIME column glowing cyan-green on the right, with rows for FEES, KYC, and CUSTODY. The Blue Kid stands beside the table, pointing at the RZ PRIME column. Green checkmarks on the RZ side, red X marks on the CeFi side."}

E. Article: "RZ Prime fees are transparent: 3%, 6%, or 9%"
{"read": "NUMBER", "family": "data_tiles", "headline": "CLEAR FEE, CLEAR TIMING, CLEAR OUTCOME", "data_elements": [{"value": "3%", "label": "TIER 1"}, {"value": "6%", "label": "TIER 2"}, {"value": "9%", "label": "TIER 3"}], "environment": "circuit_floor", "camera": "low_angle_hero", "energy": "calm_premium", "mood_accent": "cyan_vs_green", "wolf": "none", "subject_scene": "Three ascending clear glass tiles rise from a circuit-board platform like stairs, each displaying a fee percentage in large cyan text with a tier label below, the tiles growing taller left to right, soft green glow on the highest tier."}

F. Article: "In a space where humans make mistakes, code doesn't"
{"read": "THREAT", "family": "shatter", "headline": "IN A SPACE WHERE HUMANS MAKE MISTAKES CODE DOESN'T", "data_elements": [{"value": "VERIFIED", "label": ""}, {"value": "AUDITED", "label": ""}, {"value": "ON-CHAIN", "label": ""}, {"value": "CUSTODY", "label": ""}, {"value": "MIDDLEMAN", "label": ""}], "environment": "circuit_floor", "camera": "low_angle_hero", "energy": "explosive_dynamic", "mood_accent": "cyan_vs_red", "wolf": "none", "subject_scene": "A pristine glass cube at center glows cyan with VERIFIED, AUDITED, and ON-CHAIN badges in green on its faces. At the edges, crumbling legacy elements labeled CUSTODY and MIDDLEMAN shatter outward with red X marks and alarm-red cracks, fragments suspended mid-air. Circuit-board floor with glowing traces radiates beneath the intact cube."}
""".strip(),
    },
    'Coin Hall': {
        'brand_name': 'Coin Halls',
        'brand_tagline': "a luxury Web3 prediction-game brand set in a 1920s Art Deco mansion world, where "
                         "holographic on-chain data lives inside classical opulence",
        'headline_max_words': 7,
        'headline_uppercase': False,
        'mood_accent_default': 'gold',
        'mood_accent_restricted': {'gold_vs_mono': 'contrast'},
        'axis_optional': {'hall_theme': True},
        'data_element_template': 'an engraved gold plaque or glowing holographic panel displaying "{value}"{label_part}',
        'data_element_label_template': ' next to the label "{label}"',
        'legibility_line': "All lettering is large, elegant, crisp and clearly legible, engraved gold serif style.",
        'anti_repetition_rules': (
            "Hard rules: do not repeat the same family more than 2 times in a row; do not use the "
            "'grand_hall' environment more than 3 times in a row; use the 'society' family at most "
            "once every 4 posts; include a hall_theme other than 'none' at least once every 5 posts; "
            "include a holographic/on-chain element in at least 2 of every 3 posts."
        ),
        # §0 — Frozen brand layer: never varies, never touches an LLM.
        'frozen_style': {
            'format': "vertical 4:5 editorial poster set in a 1920s Art Deco / Gatsby-era luxury world -- grand "
                      "mansion interiors and estates, rendered as cinematic photographic realism, NOT glossy "
                      "3D-render and NOT neon sci-fi",
            'palette': "near-black and deep warm brown base, with champagne gold, brass and amber as the dominant "
                       "accent, and warm candlelight / chandelier glow throughout. The one permitted tech color is "
                       "a faint teal-emerald holographic glow, used sparingly",
            'materials': "black marble with gold veining, polished brass, crystal chandeliers, aged paper, "
                         "leather-bound ledgers, velvet, gold engraving, candle flame",
            'rendering': "warm, low-key, candlelit / chandelier-lit cinematic photography with dramatic shadows "
                         "and golden reflections on polished marble floors; elegant figures in evening wear, "
                         "silhouettes and candlelit crowds are allowed and encouraged, with faces stylized-cinematic "
                         "and never recognizable real people",
            'background_vocab': "the brand's signature fusion -- holographic on-chain data living inside the "
                                 "classical world: teal glass panels with predictions or timestamps floating over "
                                 "marble, data light-streams entering windows, glowing verified-price tags. Most "
                                 "images contain at least one subtle on-chain element; the technology is a guest "
                                 "in the mansion, never the architecture",
            'headline_zone': "the top zone carries the headline in elegant letter-spaced SERIF type in gold or "
                             "champagne, often framed by Art Deco ornamental borders with corner flourishes; mixed "
                             "case or small-caps is allowed",
            'never': "no neon cyberpunk, no sci-fi corridors, no frosted-glass cube aesthetics, no daylight or "
                     "office settings, no casual or cartoon style, no white backgrounds, no recognizable real "
                     "people, no real luxury-brand logos or names, no paragraphs of text, no small dense labels",
        },
        # §0 metaphor library — shared visual vocabulary the Art Director can draw on.
        'metaphors': {
            "timing / timestamps":               "an antique pocket watch, grandfather clock, or hourglass",
            "oracle / verified price":            "brass scales of justice, a wax-sealed verdict, or an illuminated 'verified' tag",
            "entries / records / on-chain log":   "a handwritten ledger, fountain pen, wax seal, or holographic registry board",
            "the pot / prize":                    "a golden trophy cup overflowing with light or coins",
            "the halls / choices":                "grand doors, archways, or corridors of doors with engraved signs",
            "blockchain / on-chain proof":        "teal holographic glass panels, data light-streams, or glowing constellation lines",
            "skill / precision":                  "a chess piece, telescope, compass, or magnifying glass over numbers",
            "chaos / gambling / the old way":     "blurred monochrome casino noise, roulette motion blur, or scattered chips",
            "the platform itself":                "the mansion or chateau at night, with glowing windows",
            "hall themes":                        "a sculptural luxury automobile (car), a diamond on velvet (jewelry), vintage "
                                                   "luggage with a glass horizon (trip), brass machinery and gears (industrial), "
                                                   "or a skyline beyond arched windows (real estate)",
        },
        # §1 — Layout families F1-F8 (artifact/contrast/registry/doors/procession/reveal/hologram/society).
        'families': {
            'artifact': {
                'name': "ARTIFACT",
                'skeleton': "ONE exquisite object sits in macro/close-up on black marble -- a pocket watch, brass "
                            "scales, trophy, ledger, diamond, or key -- candlelit with shallow depth of field, a "
                            "dim mansion room blurred behind. The object may carry one short engraved or displayed value.",
                'text_policy': "Headline plus at most ONE in-scene value displayed on the object itself (a number, "
                               "a date, or 1-4 words). Prefer art_only or a single data element.",
                'default_axes': {'environment': 'marble_table', 'camera': 'close_up_macro', 'energy': 'quiet_prestige'},
                'data_budget': 1,
            },
            'contrast': {
                'name': "CONTRAST",
                'skeleton': "The frame is split left/right. The negative side is desaturated, monochrome and "
                            "motion-blurred -- casino noise, roulette wheels, frantic crowds, scattered chips. The "
                            "positive side is still, warm and golden -- composed figures in an Art Deco hall under "
                            "chandelier light, ordered and calm. A clean vertical seam or architectural divide "
                            "separates the two sides.",
                'text_policy': "Headline only, ideally spanning the seam. At most one short label per side if essential.",
                'default_axes': {'environment': 'grand_hall', 'camera': 'eye_level_wide', 'energy': 'dramatic_tension'},
                'data_budget': 2,
            },
            'registry': {
                'name': "REGISTRY",
                'skeleton': "Either (a) a teal holographic board floats above a marble pedestal in a candlelit "
                            "hall, listing 2-4 large values with one row highlighted gold as the winner or record; "
                            "or (b) an open aged ledger lies on marble with 2-3 large handwritten entries, a "
                            "fountain pen, and a wax seal.",
                'text_policy': "Headline plus at most 3 value+label pairs. Values are 1-6 characters (e.g. $85.34, "
                               "$12.4M); labels are 1-2 words. Each value rendered large on its own row or line. "
                               "No timestamps as microtext.",
                'default_axes': {'environment': 'grand_hall', 'camera': 'low_angle_pedestal', 'energy': 'quiet_prestige'},
                'data_budget': 3,
            },
            'doors': {
                'name': "DOORS OF OUTCOME",
                'skeleton': "2-3 grand doors or archways stand in a marble corridor, each with a short engraved "
                            "sign above. A golden light-path on the floor splits and flows toward them; doors may "
                            "glow differently -- warm and open vs dim and closed -- to show outcomes.",
                'text_policy': "Headline plus at most 3 engraved door signs of 1-3 words each, large.",
                'default_axes': {'environment': 'door_corridor', 'camera': 'one_point_symmetry', 'energy': 'quiet_prestige'},
                'data_budget': 3,
            },
            'procession': {
                'name': "HALL PROCESSION",
                'skeleton': "A symmetrical row of 3-5 ornate doors or archways under a chandelier (the five-halls "
                            "shot), or three objects on marble pedestals along a corridor, each step represented "
                            "by an icon-object (door, ledger, trophy) connected by a golden floor inlay.",
                'text_policy': "Headline plus at most 3 short labels (1-2 words) on signs above doors or pedestals. "
                               "For the five-hall establishing shot, use hall names (CAR, JEWELRY, TRIP, "
                               "INDUSTRIAL, REAL ESTATE) but show only 3 visible signs, with the rest implied.",
                'default_axes': {'environment': 'grand_hall', 'camera': 'one_point_symmetry', 'energy': 'quiet_prestige'},
                'data_budget': 3,
            },
            'reveal': {
                'name': "REVEAL",
                'skeleton': "Scale and unveiling: the chateau at night with glowing windows beneath a "
                            "constellation-lined sky, or a trophy cup swelling with golden light at the end of a "
                            "long hall, or curtains drawing back from a prize. A small dim foreground gives way "
                            "to a grand, glowing subject.",
                'text_policy': "Headline plus optionally one value (the prize or pot figure) on a plaque or holo tag.",
                'default_axes': {'environment': 'estate_exterior', 'camera': 'eye_level_wide', 'energy': 'ceremonial_awe'},
                'data_budget': 1,
            },
            'hologram': {
                'name': "HOLOGRAM IN THE HALL",
                'skeleton': "Teal holographic elements materialize inside the classical space -- a holo panel "
                            "hovering above a marble table showing a glowing checkmark or seal, a stream of "
                            "luminous data flowing through a window into a ledger, or ghostly constellation lines "
                            "connecting a chandelier to a verified-price tag. The classical room dominates; the "
                            "hologram accent fills roughly 20% of the frame.",
                'text_policy': "Headline plus at most 2 short holo labels (e.g. 'VERIFIED', one value). Any "
                               "diagrammatic content is abstract and wordless.",
                'default_axes': {'environment': 'study_library', 'camera': 'eye_level_wide', 'energy': 'quiet_prestige'},
                'data_budget': 2,
            },
            'society': {
                'name': "SOCIETY SCENE",
                'skeleton': "Elegant evening-dress figures populate the hall -- a celebrated winner under a "
                            "spotlight, an applauding crowd around a prize, or guests with faint holo "
                            "prediction-tags floating beside them. Cinematic group staging, golden light, marble "
                            "reflections.",
                'text_policy': "Headline plus at most 2 short holo-tag values, or one plaque line (e.g. 'CAR "
                               "HALL'). Never wallet addresses or long strings.",
                'default_axes': {'environment': 'grand_hall', 'camera': 'eye_level_wide', 'energy': 'ceremonial_awe'},
                'data_budget': 2,
            },
        },
        # §3 — Variation axes: each value maps to a fixed sentence used by the assembler.
        'axes': {
            'environment': {
                'grand_hall':      "The setting is a grand Art Deco hall, with crystal chandeliers, columns, and "
                                   "a black marble floor inlaid with gold.",
                'study_library':   "The setting is an intimate wood-paneled study or library, with a desk lamp, "
                                   "a leather-bound ledger, and a glass of whisky.",
                'door_corridor':   "The setting is a marble corridor lined with ornate doors and archways, "
                                   "receding into the depth of the frame.",
                'marble_table':    "The setting is an extreme close-up world: a single object resting on a black "
                                   "marble surface, candlelight reflecting off the stone.",
                'estate_exterior': "The setting is the grand chateau at night, its windows glowing warmly beneath "
                                   "a starlit, constellation-lined sky.",
                'gallery_balcony': "The setting is a mezzanine gallery overlooking the grand hall below, with "
                                   "ornate railings and deep architectural shadow.",
            },
            'camera': {
                'close_up_macro':    "The camera is in extreme close-up, macro focus on the texture and surface "
                                     "detail of the central object.",
                'eye_level_wide':    "The camera is a cinematic eye-level wide establishing shot.",
                'one_point_symmetry':"The camera is positioned frontally with one-point symmetry, looking "
                                     "straight down a corridor or row of doors.",
                'low_angle_pedestal':"The camera looks up at a pedestal or holographic board from a low angle.",
                'over_shoulder':     "The camera looks past a silhouetted guest toward the subject.",
            },
            'energy': {
                'quiet_prestige':   "The lighting is still and confident, candlelit and golden, conveying quiet prestige.",
                'dramatic_tension': "The lighting is high-contrast with deep shadows and a single hard light "
                                    "source, creating dramatic tension.",
                'ceremonial_awe':   "The scene is lit like a ceremonial spotlight moment, with swirling light and "
                                    "a sense of celebration.",
            },
            'hall_theme': {
                'car':         "A sculptural luxury automobile silhouette with brass engine details is woven into "
                               "the scene, evoking the Car Hall.",
                'jewelry':     "A diamond or necklace resting on dark velvet, catching candle glints, is woven "
                               "into the scene, evoking the Jewelry Hall.",
                'trip':        "Vintage travel luggage and a glass horizon traced with golden map lines are woven "
                               "into the scene, evoking the Trip Hall.",
                'industrial':  "Polished brass machinery and gears with a forge-like glow are woven into the "
                               "scene, evoking the Industrial Hall.",
                'real_estate': "A skyline glimpsed beyond arched windows, alongside an architectural model on "
                               "marble, is woven into the scene, evoking the Real Estate Hall.",
            },
            'mood_accent': {
                'gold':       "The dominant accent color throughout the scene is champagne gold and brass.",
                'gold_teal':  "The dominant accent blends champagne gold with the brand's teal-emerald "
                              "holographic glow, for scenes carrying on-chain elements.",
                'gold_vs_mono':"The scene contrasts champagne gold and warm light on the positive side against "
                               "desaturated monochrome on the negative side.",
            },
        },
        # §2 — News-type -> family routing guidance for the Art Director.
        'routing_table': """
News category -> Primary family (fallback):
- Auction results / collectible price records -> registry (fallback: artifact)
- Luxury category news (cars, watches, jewelry, travel, real estate) -> artifact (fallback: society)
- Luxury market trends / wealth reports -> registry (fallback: reveal)
- Oracle / price feeds / Chainlink / Pyth -> hologram (fallback: artifact)
- Smart-contract fairness / transparency / timestamps -> hologram (fallback: doors)
- No-KYC / wallet-based access -> hologram (fallback: contrast)
- Web3 gaming / entertainment market context -> contrast (fallback: society)
- Gambling-vs-skill / positioning / FUD -> contrast (fallback: artifact)
- How-it-works / mechanics explainers -> doors (fallback: procession)
- Platform overview / five halls -> procession (fallback: reveal)
- Winner / prize / pot announcements -> society (fallback: reveal)
- Growth / big numbers / anticipation -> reveal (fallback: registry)
- Anything ambiguous -> artifact

Tie-breakers: prefer the family NOT used in the last 3 posts (see anti-repetition notes below). If still
tied, prefer the lower-risk family -- artifact is the safest universal fallback.
""".strip(),
        # §4 items 1-5 — global text rules for the Art Director (item 6, the legibility line, is
        # appended deterministically by the assembler).
        'text_rules': """
1. Headline: 7 words or fewer, elegant, mixed case or small-caps allowed. Big values are encouraged. Avoid
   hard-to-spell proper nouns; never use real auction-house or luxury-brand names (say THE RECORD SALE, not
   Sotheby's), and never depict real luxury-brand logos or names in the image.
2. In-scene text budget per family: artifact <=1, contrast <=2, registry <=3 value+label pairs, doors <=3
   door signs, procession <=3 labels, reveal <=1 value, hologram <=2 holo labels, society <=2 short tags.
3. Values are 1-6 characters; labels and signs are 1-3 words; render every string large on its own clean
   surface (a plaque, sign, holo panel, or ledger line).
4. Sub-headlines are not generated in-image; thin taglines belong to the overlay layer, not the prompt.
5. Never render wallet addresses, timestamps as microtext, dense lists, or paragraphs.
""".strip(),
        # Safe fallback brief used when the Art Director response is missing/invalid/banned.
        'fallback_brief': {
            'family': 'artifact',
            'headline': 'A Quiet Moment, Recorded',
            'layout': 'art_only',
            'data_elements': [],
            'environment': 'marble_table',
            'camera': 'close_up_macro',
            'energy': 'quiet_prestige',
            'mood_accent': 'gold',
            'hall_theme': 'none',
            'subject_scene': (
                "An antique gold pocket watch lies open on black marble veined with gold, its face catching "
                "warm candlelight, with the dim glow of a grand hall blurred softly behind it."
            ),
        },
        'brief_examples': """
Worked examples (for guidance only -- do not copy headlines or scenes verbatim):

A. Article: "Patek Philippe watch sells for record $12.4M at auction"
{"family": "registry", "headline": "A Record Falls Under the Hammer", "layout": "art_with_data", "data_elements": [{"value": "$12.4M", "label": "HAMMER"}, {"value": "x3", "label": "ESTIMATE"}], "environment": "grand_hall", "camera": "low_angle_pedestal", "energy": "quiet_prestige", "mood_accent": "gold_teal", "hall_theme": "jewelry", "subject_scene": "A teal holographic registry board hovers above a black marble pedestal in a candlelit Art Deco hall, two glowing ledger rows displaying the record figures with the top row haloed in gold; below, a diamond necklace rests on dark velvet catching candlelight, while blurred evening-dress silhouettes watch from the shadows."}

B. Article: "Chainlink launches new low-latency price feeds"
{"family": "hologram", "headline": "The Oracle Just Got Faster", "layout": "art_with_data", "data_elements": [{"value": "VERIFIED", "label": ""}], "environment": "study_library", "camera": "eye_level_wide", "energy": "quiet_prestige", "mood_accent": "gold_teal", "hall_theme": "none", "subject_scene": "A teal stream of luminous data pours through a tall window onto an open ledger on a wood-paneled desk, while a brass scale beside it tips gently into balance, one holographic tag glowing above the ledger."}

C. Article: "Global luxury car market hits new high"
{"family": "artifact", "headline": "Motion Has Never Been Worth More", "layout": "art_with_data", "data_elements": [{"value": "CAR HALL", "label": ""}], "environment": "marble_table", "camera": "close_up_macro", "energy": "quiet_prestige", "mood_accent": "gold_teal", "hall_theme": "car", "subject_scene": "A sculptural brass automobile model rests on black marble, candlelight catching its curves, with faint teal constellation lines tracing its silhouette and a small engraved plaque beside it."}

D. Article: "Survey: users abandoning casino dApps for skill-based games"
{"family": "contrast", "headline": "Luck Fades. Skill Compounds.", "layout": "art_only", "data_elements": [], "environment": "grand_hall", "camera": "eye_level_wide", "energy": "dramatic_tension", "mood_accent": "gold_vs_mono", "hall_theme": "none", "subject_scene": "On the left, monochrome motion-blurred slot machines and frantic figures dissolve into noise; on the right, a still golden Art Deco hall where composed guests in evening wear study a glowing registry board, a clean marble seam dividing the two worlds."}

E. Article: "Car Hall winner announced"
{"family": "society", "headline": "The Pot Found Its Owner", "layout": "art_with_data", "data_elements": [{"value": "CAR HALL", "label": ""}], "environment": "grand_hall", "camera": "eye_level_wide", "energy": "ceremonial_awe", "mood_accent": "gold_teal", "hall_theme": "car", "subject_scene": "A spotlight falls on an applauded winner in evening dress beside a veiled sculptural automobile in a grand Art Deco hall, golden confetti light drifting down, with one holographic plaque glowing softly nearby."}

F. Article: "What happens at the final reveal?"
{"family": "doors", "headline": "Every Pot Finds Its Owner", "layout": "art_with_data", "data_elements": [{"value": "EXACT", "label": ""}, {"value": "FIRST", "label": ""}, {"value": "CLOSEST", "label": ""}], "environment": "door_corridor", "camera": "one_point_symmetry", "energy": "quiet_prestige", "mood_accent": "gold", "hall_theme": "none", "subject_scene": "Three arched marble doors recede down a candlelit corridor, each engraved with a single word above its frame, a golden light-path splitting across the floor toward them with the leftmost door glowing warmly open."}
""".strip(),
        'extra_banned_subject_terms': [
            'rolex', 'patek philippe', "sotheby's", 'sothebys', "christie's", 'christies',
            'rolls-royce', 'rolls royce', 'ferrari', 'lamborghini', 'wallet address',
        ],
    },
    'Meta Coin Guard': {
        'brand_name': 'Meta Coin Guard',
        'brand_tagline': 'a parametric on-chain cover protocol for Web3 -- translucent engineered glass, '
                         'dark steel platforms, and glowing circuit networks define a world where rules '
                         'are written before volatility arrives',
        'headline_max_words': 7,
        'headline_uppercase': True,
        'mood_accent_default': 'teal',
        'mood_accent_restricted': {'teal_vs_red': {'families': ['threat_vs_guard'], 'environments': ['void_storm', 'ruin_contrast']}},
        'environment_restricted': {
            'void_storm': {'energies': ['storm_tension'], 'families': ['threat_vs_guard']},
            'ruin_contrast': {'energies': ['storm_tension'], 'families': ['threat_vs_guard']},
        },
        'data_element_template': 'a glowing panel or glass surface displaying "{value}"{label_part}',
        'data_element_label_template': ' labeled "{label}"',
        'legibility_line': "All text is large, bold, crisp and clearly legible.",
        'logo_line': "A small MCG shield emblem in white or teal sits in the bottom-left corner of the frame.",
        'anti_repetition_rules': (
            "Hard rules: do not repeat the same family more than 2 times in a row; do not use "
            "'threat_vs_guard' more than 2 times in any 4 consecutive posts; do not use the "
            "'glass_dark' finish more than 4 times in a row; use the 'guardian' family at most "
            "once every 8 posts; use the 'left_block' headline_layout roughly 1 in 3 posts; "
            "the shield motif should appear in some form in every post; include a glass/transparent "
            "structure in at least 3 of every 4 posts."
        ),
        'frozen_style': {
            'format': "vertical 4:5 editorial poster set in a security-infrastructure world of translucent "
                      "engineered glass, dark steel platforms, and glowing circuit networks -- clean 3D product "
                      "visualization aesthetic, NOT photorealistic and NOT cartoon",
            'palette': "near-black charcoal base, with teal/cyan glow as the primary accent (shield outlines, "
                       "conduit traces, protected states) and purple/violet as the secondary accent (brand "
                       "shield icon, energy cores, headline gradients); headline type fades from white to "
                       "purple or from white to sage-green. Red/crimson is permitted only as the threat color "
                       "-- crashes, shattering, ruins -- and never represents the brand itself. Gold/bronze "
                       "appears only on coins, premium badges, or ranking numbers",
            'materials': "translucent engineered glass with visible circuit-board internals (the signature "
                         "material), dark gunmetal steel platforms and pedestals, circuit-board floor surfaces "
                         "with teal trace lines, teal neon conduit tubes, server rack corridors, polished "
                         "dark composite surfaces",
            'rendering': "clean high-contrast stylized 3D product-visualization with cinematic rim-lighting "
                         "in teal and purple; dark dramatic shadows; glass objects are transparent and "
                         "luminous, not frosted or blurry; no humans except the faceless armored Guardian "
                         "figure or anonymous silhouettes in conceptual scenes",
            'background_vocab': "the shield motif is the brand's universal anchor -- a 3D metallic shield, "
                                 "a glowing teal outline, a glass shield frame, or an embossed badge -- "
                                 "alongside circuit-board terrain, teal conduit lines connecting structures, "
                                 "and server-rack corridor environments",
            'headline_zone': "the headline is set in bold geometric sans-serif UPPERCASE type, white or "
                             "fading from white to purple, positioned centered in a top zone or stacked "
                             "in a left-aligned editorial block",
            'never': "no frosted/blurry glassmorphism (glass must be CLEAR and transparent), no gold "
                     "Art Deco or classical luxury, no wireframe-only voids, no daylight or white "
                     "backgrounds, no casual or cartoon style, no recognizable real people, no real "
                     "logos, no paragraphs of text, no micro-labels",
        },
        'metaphors': {
            "protection / the Guard": "a shield -- 3D metallic, glowing teal outline, translucent glass form, or embossed badge",
            "the protocol / rules": "a terminal window with short glowing code, or engraved logic lines on a glass panel",
            "threat / volatility / crashes": "shattering glass objects, falling red candlestick charts, crumbling structures "
                                              "with red embers, or collapsing dominoes",
            "time pressure / missed moment": "a shattering hourglass with glass shards and spilling sand",
            "custody risk / drained funds": "a breached vault or crumbling institutional building leaking red light",
            "user's assets / wallet": "a dark leather-and-metal wallet with a glowing shield emblem, or a sealed case",
            "non-custodial / user control": "the wallet standing untouched outside the vault, with no key held by anyone",
            "on-chain verification / audit": "a glowing green checkmark seal, a verified badge, or teal scan lines",
            "liquidity / capital flows": "a translucent glass wave or flowing teal light streams",
            "oracle / data feeds": "luminous data conduits feeding a console, teal energy streams, or price tickers on dark panels",
            "monitoring / transparency": "a holographic command table, transparent glass structures with visible internals",
            "plans / tiers": "glass-and-steel blocks in ascending steps, or metal shield badges in silver, gold, and platinum",
            "discipline / structure": "a calm figure or shield standing solid while chaos surrounds it",
            "the platform / app": "a dark UI card showing wallet balance and green checkmark, framed by a glass shield",
        },
        'families': {
            'shield_hero': {
                'name': "SHIELD HERO",
                'skeleton': "ONE large shield dominates the frame as the central hero object -- it can be a "
                            "3D metallic shield, a glowing teal shield outline, or a translucent glass shield "
                            "with visible circuitry inside -- sitting on a dark steel pedestal or platform, "
                            "with teal conduit traces converging toward it and a circuit-board floor beneath.",
                'text_policy': "Headline plus at most 1 short label or value displayed on the shield face "
                               "(e.g. 'YOUR GUARD', a percentage, or 1-4 words). Prefer art_only.",
                'default_axes': {'environment': 'steel_platform', 'camera': 'low_angle_hero', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 1,
            },
            'threat_vs_guard': {
                'name': "THREAT vs GUARD",
                'skeleton': "A two-zone confrontation in flexible geometry (left/right, top/bottom, or "
                            "background/foreground): one zone is the THREAT -- shattering glass objects, "
                            "crashing red candlestick charts, crumbling structures with red embers or "
                            "smoke, collapsing dominoes, or a breached vault; the other zone is the GUARD "
                            "-- an intact shield, a transparent glass structure, or a calm wallet on a "
                            "platform, rendered in teal and purple, always visually heavier and more stable "
                            "than the chaos beside it.",
                'text_policy': "Headline plus at most 2 short zone labels (1-3 words each, e.g. 'MARKET PRICE' / "
                               "'DECLARED VALUE'). Labels on the threat side may name the threat.",
                'default_axes': {'environment': 'void_storm', 'camera': 'dutch_or_split', 'energy': 'storm_tension', 'finish': 'glass_dark'},
                'data_budget': 2,
            },
            'glass_fortress': {
                'name': "GLASS FORTRESS",
                'skeleton': "A large translucent glass-and-steel architectural structure -- a glass cube "
                            "building, a transparent server tower, or a crystal citadel -- with visible "
                            "circuit-board internals and teal energy flowing through its transparent walls. "
                            "The structure may have the MCG shield emblem embedded in or floating above it. "
                            "Often shown at monumental scale from a low angle.",
                'text_policy': "Headline plus at most 2 short labels on glass panels (e.g. 'Transparent', "
                               "'Autonomous'). Labels appear as floating holographic tags.",
                'default_axes': {'environment': 'server_corridor', 'camera': 'low_angle_hero', 'energy': 'calm_structure', 'finish': 'glass_bright'},
                'data_budget': 2,
            },
            'plan_blocks': {
                'name': "PLAN BLOCKS",
                'skeleton': "2-3 engineered glass-and-steel blocks stand on circuit-board terrain, arranged "
                            "in a row or as ascending steps; each block is a translucent glass platform "
                            "with teal or purple internal glow, carrying one large value and one short "
                            "label; a coin badge or shield may hover above the key block.",
                'text_policy': "Headline plus at most 3 value+label pairs. Values are 1-6 characters; "
                               "labels are 1-2 words. Each pair isolated on its own block face, rendered large.",
                'default_axes': {'environment': 'circuit_terrain', 'camera': 'isometric_high', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 3,
            },
            'protocol_flow': {
                'name': "PROTOCOL FLOW",
                'skeleton': "A horizontal three-node sequence connected by glowing teal arrows or conduit "
                            "lines -- three translucent glass cards, three icons on pedestals, or three "
                            "holographic stages -- each step represented by an icon or UI element "
                            "(wallet, token, smart contract, shield) showing a process left to right.",
                'text_policy': "Headline plus at most 3 step labels of 1-3 words (e.g. 'GUARD ACTIVATED', "
                               "'MARKET MOVES', 'PROTOCOL EXECUTES').",
                'default_axes': {'environment': 'steel_platform', 'camera': 'frontal_wide', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 3,
            },
            'code_terminal': {
                'name': "CODE TERMINAL",
                'skeleton': "A terminal window or stack of rule-notification panels floats as the hero "
                            "element, framed by the MCG shield outline or embedded in a glass structure; "
                            "the panels have purple neon borders and show short rule text or pseudo-code "
                            "lines; thin data threads connect the terminal to the environment.",
                'text_policy': "Headline plus at most 3 lines of short rule text or pseudo-code (each <=6 "
                               "words). Each rule panel is its own visual element with an icon.",
                'default_axes': {'environment': 'server_corridor', 'camera': 'frontal_terminal', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 3,
            },
            'dashboard': {
                'name': "DASHBOARD",
                'skeleton': "A dark UI card or app mockup sits centrally, showing a wallet balance or "
                            "Guard status with a green checkmark; the card is framed by a translucent "
                            "glass shield structure; floating badges around it display key parameters "
                            "(token, duration, plan); teal energy waves or conduit lines flow in the "
                            "background.",
                'text_policy': "Headline plus at most 3 floating badge labels (1-3 words each, e.g. "
                               "'Token: INS', 'Guard Plan: X', 'Duration: 4 months').",
                'default_axes': {'environment': 'steel_platform', 'camera': 'frontal_wide', 'energy': 'calm_structure', 'finish': 'glass_bright'},
                'data_budget': 3,
            },
            'guardian': {
                'name': "THE GUARDIAN",
                'skeleton': "The anonymous armored sentinel -- sleek dark armor with teal accent lines "
                            "and a reflective visor, no visible face -- stands calm on a raised platform "
                            "or pedestal; an optional three-node timeline or shield projection appears "
                            "beside or behind the figure; circuit-board floor and dark environment.",
                'text_policy': "Headline plus at most 2 short labels (timeline nodes or one tag).",
                'default_axes': {'environment': 'steel_platform', 'camera': 'low_angle_hero', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 2,
            },
        },
        'axes': {
            'environment': {
                'steel_platform':  "The setting is a dark polished steel platform or pedestal, with "
                                   "circuit-board traces in the floor and teal conduit lines at the edges.",
                'server_corridor': "The setting is a corridor of glowing server racks receding into the "
                                   "distance, with teal and purple rim-lighting on the rack surfaces.",
                'circuit_terrain': "The setting is a vast landscape of circuit-board terrain stretching "
                                   "to the horizon, with teal trace lines glowing like city grids.",
                'console_deck':    "The setting is a dark operations room centered on a holographic "
                                   "command table or glass platform.",
                'void_storm':      "The setting is dark space with fragments of shattering glass and "
                                   "falling red chart candles, smoke and crimson embers.",
                'ruin_contrast':   "The setting splits: one side shows crumbling institutional buildings "
                                   "or rusted structures with red glow; the other side shows clean glass "
                                   "and teal-lit infrastructure.",
            },
            'camera': {
                'low_angle_hero':   "The camera looks up at the central object or figure from a low angle, "
                                    "making it feel monumental.",
                'isometric_high':   "The camera is a high analytical three-quarter isometric view.",
                'frontal_wide':     "The camera is a flat-on cinematic wide shot, symmetrical.",
                'frontal_terminal': "The camera faces the terminal or panel stack directly, centered.",
                'dutch_or_split':   "The camera uses a tilted angle or a two-zone split framing for "
                                    "confrontation.",
                'close_up_detail':  "The camera is in close-up on the glass surface detail, showing "
                                    "circuit internals and light refractions.",
            },
            'energy': {
                'calm_structure': "The lighting is still, ordered and confident -- clean teal and purple "
                                  "rim-lights on glass and metal.",
                'storm_tension':  "The threat is active -- red light, volumetric haze, shattering glass "
                                  "and falling chart candles charge the scene.",
                'ascendant':      "The light is rising upward, with a sense of scale reveal and growth, "
                                  "teal energy flowing upward through glass structures.",
            },
            'mood_accent': {
                'teal':        "The dominant accent color throughout the scene is teal/cyan.",
                'teal_purple': "The dominant accent blends teal/cyan with purple/violet, for "
                               "brand-core or shield-led scenes.",
                'teal_vs_red': "The scene contrasts teal and purple on the Guard's side against "
                               "red/crimson on the threat side.",
            },
            'finish': {
                'glass_dark':   "The dominant finish is dark gunmetal with translucent glass elements "
                                "glowing from within, deep shadows and neon accents.",
                'glass_bright': "The dominant finish emphasizes the glass transparency -- brighter, "
                                "more luminous, with teal and purple light filling the glass structures.",
            },
            'headline_layout': {
                'centered_top': "the headline is centered in a clean top zone of the frame.",
                'left_block':   "the headline is stacked in a left-aligned editorial block.",
            },
        },
        'routing_table': """
News category -> Primary family (fallback):
- Hacks / exploits / drained protocols -> threat_vs_guard (fallback: shield_hero)
- Market crashes / volatility spikes -> threat_vs_guard (fallback: shield_hero)
- Smart-contract security / audits -> code_terminal (fallback: glass_fortress)
- Rule-based / automated settlement -> code_terminal (fallback: protocol_flow)
- Non-custodial design / user control -> shield_hero (fallback: glass_fortress)
- Wallet monitoring / on-chain visibility -> dashboard (fallback: code_terminal)
- Oracle reliability / price feeds -> dashboard (fallback: code_terminal)
- DeFi metrics / TVL / fees -> plan_blocks (fallback: dashboard)
- Policy / regulation / sanctions -> threat_vs_guard in glass_bright finish (fallback: glass_fortress)
- Institutional Web3 adoption -> glass_fortress in glass_bright finish (fallback: shield_hero)
- Multi-chain / protocol expansion -> glass_fortress (fallback: dashboard)
- How-it-works / plans / mechanics -> protocol_flow (fallback: code_terminal)
- Plan comparisons / tiers / pricing -> plan_blocks (fallback: protocol_flow)
- Psychology / discipline / panic -> guardian (fallback: threat_vs_guard)
- Product / app features / UX -> dashboard (fallback: protocol_flow)
- Anything ambiguous -> shield_hero

Tie-breakers: prefer the family NOT used in the last 3 posts (see anti-repetition notes below). If still
tied, prefer the lower-risk family -- shield_hero is the safest universal fallback. The threat_vs_guard
family will naturally dominate given the security news flow; the anti-repetition rules keep it from
monopolizing the feed.
""".strip(),
        'text_rules': """
1. Headline: 7 words or fewer, bold UPPERCASE sans, white or fading to purple or sage-green.
   Avoid hard-to-spell proper nouns; refer to protocols and companies by concept (e.g. THE BRIDGE EXPLOIT,
   not the protocol's name) -- this also avoids implying accusations on developing incident news. Tickers
   (BTC, ETH, SOL) are safe to use.
2. In-scene text budget per family: shield_hero <=1 label, threat_vs_guard <=2 zone labels, plan_blocks <=3
   value+label pairs, code_terminal <=3 rule lines (<=6 words each), protocol_flow <=3 step labels,
   glass_fortress <=2 holo labels, dashboard <=3 badge labels, guardian <=2 labels.
3. Values are 1-6 characters; labels are 1-3 words; render every string large on its own clean glass or
   steel surface.
4. Sub-headlines are not generated in-image; they belong to the overlay layer, not the prompt.
5. Never render wallet addresses, dense dashboards, readable candlestick charts, or paragraphs of text.
""".strip(),
        'fallback_brief': {
            'family': 'shield_hero',
            'headline': 'THE GUARD HOLDS',
            'layout': 'art_only',
            'data_elements': [],
            'environment': 'steel_platform',
            'camera': 'low_angle_hero',
            'energy': 'calm_structure',
            'mood_accent': 'teal',
            'finish': 'glass_dark',
            'headline_layout': 'centered_top',
            'subject_scene': (
                "A translucent glass shield with visible circuit-board internals stands on a dark "
                "polished steel pedestal, glowing with teal light from within, teal conduit traces "
                "converging toward it across the circuit-board floor, server rack silhouettes fading "
                "into shadow behind it."
            ),
        },
        'brief_examples': """
Worked examples (for guidance only -- do not copy headlines or scenes verbatim):

A. Article: "Bridge protocol exploited for $120M"
{"family": "threat_vs_guard", "headline": "PROTOCOLS FALL, RULES DON'T", "layout": "art_with_data", "data_elements": [{"value": "$120M", "label": "DRAINED"}], "environment": "ruin_contrast", "camera": "dutch_or_split", "energy": "storm_tension", "mood_accent": "teal_vs_red", "finish": "glass_dark", "headline_layout": "centered_top", "subject_scene": "The left side shows crumbling server structures with red ember glow and smoke, labeled panels falling from rusted walls; the right side shows the MCG shield standing intact on a clean glass platform connected by teal conduit lines, transparent glass panels with visible circuitry glowing steadily behind it."}

B. Article: "Major audit firm publishes smart-contract security report"
{"family": "code_terminal", "headline": "CLEAR RULES FAVOR CLEAR CODE", "layout": "art_with_data", "data_elements": [{"value": "verify", "label": ""}, {"value": "execute", "label": ""}, {"value": "settle", "label": ""}], "environment": "server_corridor", "camera": "frontal_terminal", "energy": "calm_structure", "mood_accent": "teal_purple", "finish": "glass_dark", "headline_layout": "left_block", "subject_scene": "A stack of three glass-and-steel rule panels with purple neon borders floats within the outline of the MCG shield, each panel showing a short glowing line of text with a small icon, thin teal data threads anchoring the panels to the server racks behind them."}

C. Article: "DeFi TVL hits $200B milestone"
{"family": "plan_blocks", "headline": "THE FLOOR JUST GOT HIGHER", "layout": "art_with_data", "data_elements": [{"value": "$200B", "label": "TVL"}, {"value": "+40%", "label": "YOY"}], "environment": "circuit_terrain", "camera": "isometric_high", "energy": "ascendant", "mood_accent": "teal_purple", "finish": "glass_dark", "headline_layout": "centered_top", "subject_scene": "Two translucent glass-and-steel blocks stand on circuit-board terrain in ascending steps, each block glowing with teal internal light and carrying a large value on its face, a purple shield badge hovering above the taller block, teal conduit traces connecting the blocks along the ground."}

D. Article: "How the parametric cover protocol works"
{"family": "protocol_flow", "headline": "STRUCTURE BEFORE VOLATILITY", "layout": "art_with_data", "data_elements": [{"value": "ACTIVATE", "label": ""}, {"value": "MONITOR", "label": ""}, {"value": "EXECUTE", "label": ""}], "environment": "steel_platform", "camera": "frontal_wide", "energy": "calm_structure", "mood_accent": "teal", "finish": "glass_dark", "headline_layout": "centered_top", "subject_scene": "Three translucent glass cards sit in a horizontal row on a dark steel platform, connected by glowing teal arrows, the first card showing a wallet icon, the second a pulse monitor, the third a shield with checkmark, each card glowing faintly from within with circuit-board patterns visible through the glass."}

E. Article: "Why panic selling costs more than the drop"
{"family": "guardian", "headline": "PANIC IS THE EXPENSIVE PART", "layout": "art_only", "data_elements": [], "environment": "steel_platform", "camera": "low_angle_hero", "energy": "calm_structure", "mood_accent": "teal_purple", "finish": "glass_dark", "headline_layout": "centered_top", "subject_scene": "The anonymous armored sentinel stands motionless on a raised dark platform, sleek dark armor with teal accent lines and a reflective visor, a faint three-node timeline glowing behind it with teal dots connected by a horizontal line, circuit-board floor beneath and server rack silhouettes in the background."}

F. Article: "New wallet-monitoring dashboard launches"
{"family": "dashboard", "headline": "WHEN MARKETS MOVE FAST, RULES MATTER", "layout": "art_with_data", "data_elements": [{"value": "INS", "label": "Token"}, {"value": "4 mo", "label": "Duration"}], "environment": "steel_platform", "camera": "frontal_wide", "energy": "calm_structure", "mood_accent": "teal_purple", "finish": "glass_bright", "headline_layout": "centered_top", "subject_scene": "A dark UI card showing a wallet balance with a glowing green checkmark sits centrally, framed by a translucent glass shield structure with visible circuitry, floating glass badges around it display parameters, teal energy waves flowing through the background."}
""".strip(),
        'extra_banned_subject_terms': [
            'frosted glass', 'blurry glass', 'art deco', 'chandelier', 'marble', 'gatsby',
            'wallet address', 'gold luxury',
        ],
    },
    'ChainReporter': {
        'brand_name': 'ChainReporter',
        'brand_tagline': "a crypto news media outlet built on ten rotating editorial visual formats -- not "
                         "one house style, but a magazine that picks the cover treatment each story needs",
        'core_axes': ('stage', 'composition', 'energy', 'accent'),
        'headline_max_words': 7,
        'meme_enabled': False,
        'mood_accent_default': 'cr_signal',
        'mood_accent_restricted': {'free': {'families': ['type_led', 'art_drop', 'meme']}},
        'axis_companion_field': {'story_color': 'accent_justification'},
        'passthrough_fields': ['accent_justification', 'art_style'],
        'passthrough_field_schema': {
            'accent_justification': '"" unless accent is "story_color" -- 1 short phrase naming the specific story color and why',
            'art_style': '"" unless family is "art_drop" -- a short description of this post\'s rotating illustration style; must differ from recent art_style values below',
        },
        'no_text_mode': 'art_drop',
        'no_text_line': "No text, no letters, no numbers anywhere in the image.",
        'data_element_template': 'a clean tile or label displaying "{value}"{label_part}',
        'data_element_label_template': ' with the micro-label "{label}"',
        'legibility_line': "All text is large, crisp and clearly legible.",
        'anti_repetition_rules': (
            "Hard rules: do not repeat the same family more than 2 times in a row; 'duotone' may not "
            "exceed 3 of any 5 consecutive posts; 'art_drop' art_style must not repeat within 5 posts; "
            "'meme' at most 1 in 6 posts even when enabled; 'stat_card' at most 1 in 5 posts; the "
            "'cr_signal' accent must appear in at least 1 of every 3 posts."
        ),
        # §0 — Frozen brand layer: never varies, never touches an LLM. Applies to every mode.
        'frozen_style': {
            'format': "vertical 4:5 editorial poster for a crypto news media outlet",
            'palette': "one dominant accent color per post plus neutrals -- the accent can be any color, "
                       "but the image never uses many colors at once",
            'materials': "premium, mode-appropriate materials and surfaces -- glass, metal, paper, paint or "
                         "photographic textures -- never generic stock-photo or default-AI-render textures",
            'rendering': "exchange-marketing-grade craft: controlled lighting, intentional composition, one "
                         "focal idea per image (a single hero object, a single number, a single concept, or "
                         "a single joke)",
            'background_vocab': "clean modern sans-serif typography by default, with deliberate serif or "
                                 "mono type only where the mode calls for it; numbers always render biggest",
            'headline_zone': "the headline sits in a clean, uncluttered zone with no competing detail behind it",
            'never': "generic AI-slop aesthetics (glowing humanoid robots, busy neon collages), dense "
                     "disclaimers or microtext, more than 3 text elements, watermarks, or recognizable real "
                     "people generated by AI",
        },
        # §0 metaphor library — common crypto-news beats mapped to visual choices.
        'metaphors': {
            "price moves / market records": "a single giant accent-colored numeral, or a duotone "
                "chart-and-coin treatment with directional geometry (rising arcs for gains, falling shards "
                "for drops)",
            "hacks / exploits / security incidents": "fractured, cracked or shattering geometry under tense "
                "lighting, with a story-justified accent color for the protocol involved",
            "regulation / enforcement / policy": "a monochrome federal facade, seal, gavel or courthouse, "
                "with sweeping accent-color ring or panel geometry",
            "launches / listings / products": "one premium 3D hero object -- coin medallion, glass device, "
                "rocket, or sculptural logo -- on a clean stage",
            "partnerships / integrations / M&A": "two emblem medallions joined by a connector -- a bridge, "
                "a cross, or a light-spark",
            "protocol mechanics / governance / how-it-works": "a flat or isometric diagram -- stacked "
                "layers, connected nodes, or a simple machine",
            "weekly recaps / multi-stat reports": "a card-grid of stat tiles anchored by one hero 3D object",
            "announcements / statements / deep dives": "typography as the design -- huge type, minimal imagery",
            "person-centric stories (CEOs, regulators, founders)": "route to duotone with an object/scene "
                "metaphor (the gavel, the building, the seal) standing in for the person -- never a "
                "generated face",
            "daily price / mood / evergreen posts": "a standalone artwork in a rotating style with one "
                "crypto motif (a coin, chain link, or Bitcoin glyph) embedded naturally, with zero "
                "in-image text",
        },
        # §1 — Visual modes M1-M10, mapped to snake_case family keys.
        'families': {
            'duotone': {
                'name': "DUOTONE EDITORIAL",
                'skeleton': "A black-and-white photographic or photo-real subject -- an object, building, or "
                            "scene, never a generated face -- fills the frame, with ONE accent-color "
                            "geometric treatment overlaid as a color-split background, duotone wash, or "
                            "large sweeping rings or diagonal panels that interact with the subject.",
                'text_policy': "Headline only, art_only layout.",
                'default_axes': {'stage': 'photo_real', 'composition': 'full_bleed_photo', 'energy': 'newsroom_neutral', 'accent': 'cr_signal'},
                'data_budget': 0,
                'headline_treatment': "set in a clean overlay bar across the lower third, or a left-aligned editorial block",
            },
            'big_number': {
                'name': "BIG NUMBER POSTER",
                'skeleton': "A dark or single-color field holds ONE giant figure rendered in the accent "
                            "color, dominating at least 30% of the frame height, with a short supporting "
                            "line beneath it; abstract geometric or logo-derived shapes decorate the "
                            "corners, and optionally one floating 3D token or object anchors a corner.",
                'text_policy': "One giant value (1-7 characters) plus one short supporting line (<=6 words). "
                               "The value dominates the frame.",
                'default_axes': {'stage': 'studio_dark', 'composition': 'centered_hero', 'energy': 'celebratory', 'accent': 'cr_signal'},
                'data_budget': 1,
                'headline_treatment': "the giant numeral dominates the frame; the headline is set small above or below it",
            },
            'hero_object': {
                'name': "HERO OBJECT 3D",
                'skeleton': "One premium 3D object -- a coin medallion, glass device, vault, rocket, or "
                            "sculptural logo -- sits on a clean stage, rendered in glossy glass or metal "
                            "materials with controlled studio reflections.",
                'text_policy': "Headline plus at most one short label or value near the object.",
                'default_axes': {'stage': 'gradient_sweep', 'composition': 'centered_hero', 'energy': 'celebratory', 'accent': 'cr_signal'},
                'data_budget': 1,
                'headline_treatment': "set in a clean zone above or beside the object, modest scale",
            },
            'concept_photo': {
                'name': "CONCEPT PHOTO / CAMPAIGN",
                'skeleton': "A single striking photo-real scene -- a landmark, sky, or symbolic object in "
                            "the world, never an identifiable generated face -- fills the frame with "
                            "generous negative space, evoking political-ad or brand-campaign energy.",
                'text_policy': "Headline only, short and declarative (5 words or fewer ideal).",
                'default_axes': {'stage': 'photo_real', 'composition': 'full_bleed_photo', 'energy': 'newsroom_neutral', 'accent': 'cr_signal'},
                'data_budget': 0,
                'headline_treatment': "set small in the negative space as a minimal declarative tagline",
                'headline_uppercase': False,
            },
            'flat_explainer': {
                'name': "FLAT EXPLAINER",
                'skeleton': "A flat-vector or isometric illustration in a limited 2-3 color palette renders "
                            "one diagrammatic concept -- stacked layers, connected nodes, or a simple "
                            "machine -- with clean shapes and a friendly but precise tone.",
                'text_policy': "Headline plus at most 2 short labels (1-3 words each) inside the "
                               "illustration; diagram content is otherwise abstract.",
                'default_axes': {'stage': 'flat_field', 'composition': 'isometric', 'energy': 'newsroom_neutral', 'accent': 'story_color'},
                'data_budget': 2,
                'headline_treatment': "set in a clean horizontal band above the illustration",
            },
            'type_led': {
                'name': "TYPE-LED MINIMAL",
                'skeleton': "Typography is the design. Pick one sub-variant and describe it explicitly in "
                            "the subject: brutalist dark (huge white sans on black plus one 3D chrome "
                            "detail), gallery-light (a chrome or silver object on off-white with small "
                            "type), editorial serif (elegant serif over a single macro-photo texture), or "
                            "retro-mono (line art with spaced capitals).",
                'text_policy': "Headline (may render very large) plus at most one sub-element (a kicker "
                               "word or small badge).",
                'default_axes': {'stage': 'studio_dark', 'composition': 'left_type_block', 'energy': 'newsroom_neutral', 'accent': 'free'},
                'data_budget': 1,
                'headline_treatment': "may render very large, filling much of the frame",
            },
            'art_drop': {
                'name': "ART DROP",
                'skeleton': "Standalone artwork in a deliberately rotating style -- painterly illustration, "
                            "dramatic black-and-white portrait-of-an-object, chalk or craft texture, cosmic "
                            "gradient, woodcut, or similar -- with one crypto motif (a coin, chain link, or "
                            "Bitcoin glyph) embedded naturally in the art.",
                'text_policy': "Zero in-image text. The headline and price live in the social copy, not the image.",
                'default_axes': {'stage': 'texture_macro', 'composition': 'full_bleed_photo', 'energy': 'playful', 'accent': 'free'},
                'data_budget': 0,
            },
            'meme': {
                'name': "MEME / PLAYFUL",
                'skeleton': "Whatever the joke needs -- a photoreal parody product shot, an absurdist photo "
                            "composite, or candy-colored cartoon imagery -- staying at a premium craft bar "
                            "while landing the visual joke in a single beat. Never use real brand marks or logos.",
                'text_policy': "At most one short text element if the joke requires it.",
                'default_axes': {'stage': 'photo_real', 'composition': 'centered_hero', 'energy': 'playful', 'accent': 'free'},
                'data_budget': 1,
                'headline_treatment': "a single short caption-style element, if used at all",
            },
            'stat_card': {
                'name': "STAT CARD",
                'skeleton': "A clean card-grid layout holds a title block plus 2-4 rounded stat tiles, each "
                            "carrying one icon, one value and one micro-label, anchored by one hero visual "
                            "element (a 3D object or illustration) in a corner.",
                'text_policy': "Headline plus at most 4 tiles, each a value plus a 1-2 word label. This is "
                               "the text-heaviest mode -- a hard ceiling.",
                'default_axes': {'stage': 'studio_light', 'composition': 'card_grid', 'energy': 'newsroom_neutral', 'accent': 'cr_signal'},
                'data_budget': 4,
                'headline_treatment': "a bold title block spans the top of the grid",
            },
            'lockup': {
                'name': "PARTNERSHIP LOCKUP",
                'skeleton': "Two emblem medallions or badges, each carrying an abstract glyph standing in "
                            "for a real logo, are joined by a connector device -- a bridge, an X-shaped "
                            "crossing, or a light spark -- on a clean stage; alternatively, one cinematic "
                            "backdrop carries both entity names typeset in an acquisition-style layout.",
                'text_policy': "Headline plus the two entity names as short labels (<=8 characters each) -- "
                               "the one place proper nouns appear in-image.",
                'default_axes': {'stage': 'gradient_sweep', 'composition': 'centered_hero', 'energy': 'celebratory', 'accent': 'cr_signal'},
                'data_budget': 2,
                'headline_treatment': "set above the medallions, with the entity names as two short labels beneath or beside them",
                'data_value_max_len': 8,
            },
        },
        # §3 — Variation axes: each value maps to a fixed sentence used by the assembler.
        'axes': {
            'stage': {
                'studio_dark':    "The setting is a dark or single-color studio field, evenly lit and uncluttered.",
                'studio_light':   "The setting is a bright, clean studio field in soft off-white or pale neutral tones.",
                'gradient_sweep': "The setting is a smooth soft-gradient sweep, like a seamless studio backdrop curving from floor to wall.",
                'photo_real':     "The setting is a photo-real environment -- a real-world object, building, or scene rendered with documentary realism.",
                'flat_field':     "The setting is a flat, evenly-lit field of color suited to vector or isometric illustration.",
                'texture_macro':  "The setting is an extreme close-up texture world -- paper, paint, woodgrain, or other tactile material filling the frame.",
            },
            'composition': {
                'centered_hero':    "The composition centers a single hero subject in the frame, symmetrical and commanding.",
                'left_type_block':  "The composition reserves the left portion of the frame for a stacked block of typography, with supporting imagery on the right.",
                'full_bleed_photo': "The composition is a full-bleed photographic frame, the subject filling the entire image with no visible borders.",
                'split_panel':      "The composition divides the frame into two panels -- left/right or top/bottom -- contrasting two halves of the story.",
                'isometric':        "The composition is a three-quarter isometric view, giving an ordered, diagrammatic perspective.",
                'card_grid':        "The composition arranges the frame as a grid of cards or tiles around a title block.",
            },
            'energy': {
                'newsroom_neutral': "The lighting and mood are calm, controlled and editorial -- a neutral newsroom register.",
                'celebratory':      "The lighting is bright and triumphant, with a sense of milestone and momentum.",
                'tension':          "The lighting is high-contrast and charged, with fractured or unstable elements conveying tension.",
                'playful':          "The lighting and mood are light, warm and playful.",
            },
            'accent': {
                'cr_signal':   "The dominant accent color throughout the scene is ChainReporter's signal red-orange.",
                'story_color': "The dominant accent color is justified by the story itself -- green for a "
                               "green protocol's hack, gold for a gold-backed token, blue for an "
                               "ocean-themed chain -- and the reason is named in the brief.",
                'free':        "The dominant accent color is chosen freely to suit this mode's rotating style, not tied to the brand accent.",
            },
        },
        # §2 — News-type -> mode routing guidance for the Art Director.
        'routing_table': """
News category -> Primary family (fallback):
- Regulation / enforcement / policy actions -> duotone (fallback: concept_photo)
- Policy statements / bills / "moment" framing -> concept_photo (fallback: duotone)
- Hacks / exploits / security incidents -> duotone, story-color accent (fallback: big_number)
- Market records / TVL / volumes / raises -> big_number (fallback: stat_card)
- Price moves / daily market posts -> art_drop, price in caption (fallback: big_number)
- Token launches / listings / products -> hero_object (fallback: big_number)
- Partnerships / integrations / M&A -> lockup (fallback: hero_object)
- Protocol upgrades / governance / votes -> flat_explainer (fallback: type_led)
- Explainers / education / guides -> flat_explainer (fallback: duotone)
- Company / people news (CEOs, funds, institutions) -> duotone (fallback: concept_photo)
- Macro / inflation / rates -> duotone or concept_photo (fallback: big_number)
- Weekly recap / report digests -> stat_card (fallback: type_led)
- Announcements / deep-dive promos -> type_led (fallback: hero_object)
- Memecoin / viral / light stories -> meme if enabled (fallback: art_drop)
- Anything ambiguous -> duotone

Tie-breakers: prefer the family NOT used in the last 3 posts; then prefer the lower-risk family --
duotone is the safest universal fallback.
""".strip(),
        # §4 items 1-4 — global text rules for the Art Director (item 5, the legibility line, is
        # appended deterministically by the assembler).
        'text_rules': """
1. Headline: 7 words or fewer. Treatment depends on the family (overlay bar in duotone, giant in
   big_number/type_led, minimal in concept_photo, absent in art_drop). Numbers and tickers are preferred
   over proper nouns; short famous names (BITCOIN, SEC) are fine in headlines, otherwise concept-phrase the
   story instead of naming a protocol.
2. In-image text budget by family: duotone headline only; big_number one giant value plus one short line;
   hero_object at most 1 label; concept_photo headline only; flat_explainer at most 2 labels; type_led
   headline plus 1 sub-element; art_drop ZERO; meme at most 1; stat_card at most 4 tiles; lockup 2 entity names.
3. Every text element sits in its own clean zone; values render large.
4. No real logos or trademarks in-image -- use abstract glyph stand-ins. Never generate the face of a real
   person -- route person-centric stories to duotone with an object/scene metaphor (the gavel, the building,
   the seal) instead of the person.
""".strip(),
        # Safe fallback brief used when the Art Director response is missing/invalid/banned.
        'fallback_brief': {
            'family': 'duotone',
            'headline': 'CRYPTO MARKETS MOVE',
            'layout': 'art_only',
            'data_elements': [],
            'stage': 'photo_real',
            'composition': 'full_bleed_photo',
            'energy': 'newsroom_neutral',
            'accent': 'cr_signal',
            'accent_justification': '',
            'art_style': '',
            'subject_scene': (
                "A black-and-white macro photograph of a chrome coin fills the frame, its surface catching "
                "cold studio light, while two giant signal-orange ring shapes sweep across the composition "
                "from opposite corners."
            ),
        },
        'brief_examples': """
Worked examples (for guidance only -- do not copy headlines or scenes verbatim):

A. Article: "SEC approves first crypto perps framework"
{"family": "duotone", "headline": "THE DOOR OPENS FOR CRYPTO PERPS", "layout": "art_only", "data_elements": [], "stage": "photo_real", "composition": "full_bleed_photo", "energy": "newsroom_neutral", "accent": "cr_signal", "accent_justification": "", "art_style": "", "subject_scene": "A monochrome photographic close-up of a classical federal building facade fills the frame, its columns rendered in cold black-and-white; two giant signal-orange rings sweep across the composition from opposite corners, one passing behind the columns and one in front."}

B. Article: "Uniswap does $100M volume on Polygon in 24h"
{"family": "big_number", "headline": "$100M IN A SINGLE DAY", "layout": "art_with_data", "data_elements": [{"value": "$100M+", "label": "24H VOLUME"}], "stage": "studio_dark", "composition": "centered_hero", "energy": "celebratory", "accent": "story_color", "accent_justification": "Polygon violet, since the volume happened on the Polygon network", "art_style": "", "subject_scene": "A near-black studio field holds one giant violet figure reading $100M+ dominating the upper half of the frame, with a cluster of small violet dots scattered along the bottom edge."}

C. Article: "Daily Bitcoin price post -- $76,940"
{"family": "art_drop", "headline": "BITCOIN AT $76,940", "layout": "art_only", "data_elements": [], "stage": "texture_macro", "composition": "full_bleed_photo", "energy": "playful", "accent": "free", "accent_justification": "", "art_style": "vintage botanical engraving", "subject_scene": "A Bitcoin coin is rendered as the head of a sunflower, its petals radiating outward in fine engraved linework, surrounded by detailed botanical leaves and stems in the style of a 19th-century natural history print."}

D. Article: "Chainlink integrates with major L2"
{"family": "lockup", "headline": "A NEW DATA BRIDGE GOES LIVE", "layout": "art_with_data", "data_elements": [{"value": "LINK", "label": ""}, {"value": "L2NAME", "label": ""}], "stage": "gradient_sweep", "composition": "centered_hero", "energy": "celebratory", "accent": "cr_signal", "accent_justification": "", "art_style": "", "subject_scene": "Two chrome medallions, each engraved with an abstract geometric glyph, sit side by side on a soft gradient stage, joined by a glowing signal-orange light-bridge arcing between them."}

E. Article: "How restaking actually works"
{"family": "flat_explainer", "headline": "RESTAKING, EXPLAINED", "layout": "art_with_data", "data_elements": [{"value": "STAKE", "label": ""}, {"value": "EARN", "label": ""}], "stage": "flat_field", "composition": "isometric", "energy": "newsroom_neutral", "accent": "story_color", "accent_justification": "teal and white, a calm two-color palette suited to a clean technical explainer", "art_style": "", "subject_scene": "Three flat translucent slabs are stacked in isometric perspective, with small coin shapes flowing in a cycle between them via simple arrows, rendered in a clean two-color illustration style."}

F. Article: "Weekly market recap: 4 key numbers"
{"family": "stat_card", "headline": "THE WEEK IN NUMBERS", "layout": "art_with_data", "data_elements": [{"value": "+4.2%", "label": "BTC"}, {"value": "+6.8%", "label": "ETH"}, {"value": "$182B", "label": "TVL"}, {"value": "+38%", "label": "TOP GAINER"}], "stage": "studio_light", "composition": "card_grid", "energy": "newsroom_neutral", "accent": "cr_signal", "accent_justification": "", "art_style": "", "subject_scene": "A bright off-white studio field holds a grid of four rounded stat tiles beneath a bold title block, each tile carrying one icon and one large value, with a small 3D chart-arrow object anchoring the bottom-right corner."}

G. Article: "DOGE pumps 40% on viral moment" (only reachable if meme_enabled is turned on)
{"family": "meme", "headline": "DOGE GOES TO THE MOON, LITERALLY", "layout": "art_only", "data_elements": [], "stage": "photo_real", "composition": "centered_hero", "energy": "playful", "accent": "story_color", "accent_justification": "earthlight green, matching the rising chart in the joke", "art_style": "", "subject_scene": "A photoreal shiba inu in a tiny astronaut suit sits calmly on the lunar surface sipping from a coffee cup, while a glowing green candlestick chart rises across the dark sky behind it, lit by soft earthlight."}
""".strip(),
        'extra_banned_subject_terms': [
            'frosted glass', 'glassmorphism', 'wireframe cube',
            'art deco', 'gold veining', 'chandelier', 'gatsby',
            'gunmetal',
            'real logo', 'real person', 'looks like',
        ],
    },
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
    promo_pitch = BRAND_PROMO_PITCH.get(media, '') if body.get('promoMode') else ''

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
        if promo_pitch:
            # Replace the editorial opening line with a promotional framing; keep all format rules.
            after_first = sys_prompt.split('\n', 1)
            promo_header = (
                f'You are writing promotional {platform} content for {media}. Sentiment: {sentiment}.\n'
                f'PRODUCT: {promo_pitch}\n'
                'YOUR JOB: Hook with this news article, then bridge naturally to a key product advantage '
                'made timely by this news. End with the brand benefit. Stay credible — no hype, no empty promises.\n'
            )
            sys_prompt = promo_header + (after_first[1] if len(after_first) > 1 else '')
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

    brand_tag = BRAND_HASHTAGS.get(media)
    if brand_tag:
        for v in variants:
            v['hashtags'] = [brand_tag] + [t for t in v['hashtags'] if t.lower() != brand_tag.lower()]

    primary = variants[0]
    return {
        'variants': variants,
        'copy': primary['copy'],
        'hashtags': primary['hashtags'],
        'charCount': len(primary['copy']),
        'platform': platform,
    }


# ── Anti-repetition memory for the Art Director (in-memory, resets on restart) ──
_RECENT_BRIEFS = {}

def _remember_brief(media, brief, profile):
    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    lst = _RECENT_BRIEFS.setdefault(media, [])
    lst.append({
        'family': brief.get('family'),
        env_axis: brief.get(env_axis),
        cam_axis: brief.get(cam_axis),
        'scene': (brief.get('subject_scene') or '')[:140],
        **{axis: brief.get(axis) for axis in _extra_axes(profile)},
        **{field: brief.get(field) for field in profile.get('passthrough_fields', [])},
    })
    del lst[:-10]


# ── Stage 1: Art Director LLM ──────────────────────────────────────────────────
ART_DIRECTOR_TEMPERATURE = 0.95
ART_DIRECTOR_MAX_TOKENS = 900

_CORE_AXES = ('environment', 'camera', 'energy', 'mood_accent')

def _extra_axes(profile):
    return [k for k in profile['axes'] if k not in profile.get('core_axes', _CORE_AXES)]


def _active_families(profile):
    families = profile['families']
    if profile.get('meme_enabled', True) or 'meme' not in families:
        return families
    return {k: v for k, v in families.items() if k != 'meme'}


def _build_brief_schema(profile):
    axes = profile['axes']
    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    family_enum = ' | '.join(_active_families(profile).keys())
    env_enum    = ' | '.join(axes[env_axis].keys())
    camera_enum = ' | '.join(axes[cam_axis].keys())
    energy_enum = ' | '.join(axes[nrg_axis].keys())
    mood_enum   = ' | '.join(axes[mood_axis].keys())
    max_words   = profile.get('headline_max_words', 6)
    case_note   = 'UPPERCASE' if profile.get('headline_uppercase', True) else 'mixed case'

    prefix_lines = ''
    for field, hint in profile.get('brief_prefix_schema', {}).items():
        prefix_lines += f'  "{field}": "{hint}",\n'

    extra_field_lines = ''
    axis_optional = profile.get('axis_optional', {})
    for axis in _extra_axes(profile):
        enum = ' | '.join(axes[axis].keys())
        if axis_optional.get(axis):
            enum += ' | none'
        extra_field_lines += f'  "{axis}": "{enum}",\n'

    for field, description in profile.get('passthrough_field_schema', {}).items():
        extra_field_lines += f'  "{field}": "{description}",\n'

    return f"""
Respond with ONLY a single JSON object, no markdown fences and no commentary, matching this schema exactly:
{{
{prefix_lines}  "family": "{family_enum}",
  "headline": "<= {max_words} words, {case_note}",
  "data_elements": [{{"value": "...", "label": "..."}}],
  "{env_axis}": "{env_enum}",
  "{cam_axis}": "{camera_enum}",
  "{nrg_axis}": "{energy_enum}",
  "{mood_axis}": "{mood_enum}",
{extra_field_lines}  "subject_scene": "1-3 sentences describing the central subject and any in-scene text exactly as it should appear. Never use the words text, label, logo or watermark, and never mention brand names."
}}
""".strip()


def _build_art_director_system_prompt(profile, recent, brand_mode=True):
    fs = profile['frozen_style']
    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    style_block = (
        f"Format: {fs['format']}.\n"
        f"Palette: {fs['palette']}.\n"
        f"Materials: {fs['materials']}.\n"
        f"Rendering: {fs['rendering']}.\n"
        f"Background vocabulary: {fs['background_vocab']}.\n"
        f"Headline zone: {fs['headline_zone']}.\n"
        f"Never: {fs['never']}."
    )

    metaphor_lines = '\n'.join(f"- {k}: {v}" for k, v in profile['metaphors'].items())

    families_block = '\n'.join(
        f"- {key} ({fam['name']}): {fam['skeleton']} Text policy: {fam['text_policy']} "
        f"Default axes: {env_axis}={fam['default_axes'][env_axis]}, "
        f"{cam_axis}={fam['default_axes'][cam_axis]}, {nrg_axis}={fam['default_axes'][nrg_axis]}. "
        f"Max data_elements: {fam['data_budget']}."
        for key, fam in _active_families(profile).items()
    )

    axes = profile['axes']
    axis_optional = profile.get('axis_optional', {})
    axes_block = (
        f"{env_axis}: " + ', '.join(axes[env_axis].keys()) + "\n"
        f"{cam_axis}: " + ', '.join(axes[cam_axis].keys()) + "\n"
        f"{nrg_axis}: " + ', '.join(axes[nrg_axis].keys()) + "\n"
        f"{mood_axis}: " + ', '.join(axes[mood_axis].keys())
    )
    extra_axes = _extra_axes(profile)
    for axis in extra_axes:
        enum = ', '.join(axes[axis].keys())
        if axis_optional.get(axis):
            enum += ', none'
        axes_block += f"\n{axis}: {enum}"

    passthrough_fields = profile.get('passthrough_fields', [])
    if recent:
        recent_lines = '\n'.join(
            f"- family={r['family']}, {env_axis}={r.get(env_axis)}, {cam_axis}={r.get(cam_axis)}"
            + ''.join(f", {axis}={r.get(axis)}" for axis in extra_axes)
            + ''.join(f", {field}={r.get(field)}" for field in passthrough_fields)
            + f", scene=\"{r['scene']}\""
            for r in recent
        )
        recent_block = (
            "Recently used briefs (most recent last) -- choose a different combination, do not "
            "reuse these scene concepts:\n" + recent_lines + "\n\n"
            + profile['anti_repetition_rules']
        )
    else:
        recent_block = "No recent briefs yet -- any combination is fine."

    wolf_desc = profile.get('wolf_descriptions', {})
    wolf_section = ''
    if wolf_desc and brand_mode:
        lines = '\n'.join(f"- {k}: {v}" for k, v in wolf_desc.items())
        wolf_section = f"\n\nCHARACTER CASTING (add to any family by setting the `wolf` axis):\n{lines}"

    return (
        f"You are the Art Director for {profile['brand_name']}, {profile['brand_tagline']}. Given "
        "a news article and its social copy, you design the VISUAL BRIEF for an editorial poster "
        "image. You never write final prompts or render images -- a deterministic system does "
        "that from your brief. Be creative and varied within the brand's frozen visual contract below.\n\n"
        f"FROZEN BRAND STYLE (do not restate this -- it is applied automatically):\n{style_block}\n\n"
        f"VISUAL METAPHOR LIBRARY:\n{metaphor_lines}\n\n"
        f"LAYOUT FAMILIES:\n{families_block}"
        f"{wolf_section}\n\n"
        f"VARIATION AXES (pick one value per axis from these lists):\n{axes_block}\n\n"
        f"ROUTING GUIDANCE:\n{profile['routing_table']}\n\n"
        f"TEXT RULES:\n{profile['text_rules']}\n\n"
        f"ANTI-REPETITION:\n{recent_block}\n\n"
        f"{_build_brief_schema(profile)}\n\n{profile['brief_examples']}"
    )


def call_art_director(article, copy_text, sentiment, platform, profile, recent, brand_mode=True):
    sys_prompt = _build_art_director_system_prompt(profile, recent, brand_mode=brand_mode)
    user_msg = (
        f"Article title: {article.get('title', '')}\n"
        f"Description: {article.get('desc', '')}\n"
        f"Sentiment: {sentiment}\n"
        f"Platform: {platform}\n"
        f"Chosen social copy: {copy_text}\n\n"
        "Design the visual brief now. Respond with ONLY the JSON object."
    )
    msgs = [{'role': 'system', 'content': sys_prompt},
            {'role': 'user',   'content': user_msg}]
    return openrouter_chat(EDITORIAL_MODELS['gpt']['id'], msgs, ART_DIRECTOR_TEMPERATURE, ART_DIRECTOR_MAX_TOKENS)


# ── Stage 2a: brief validation + safe fallback ─────────────────────────────────
_BANNED_SUBJECT_TERMS = ['text', 'label', 'logo', 'watermark', 'rz prime', 'chainreporter', 'coin hall', 'meta coin guard']
_WALLET_ADDRESS_RE = re.compile(r'0x[a-fA-F0-9]{6,}')

def _article_mentions_brand(article, profile):
    keywords = profile.get('brand_keywords', [])
    if not keywords:
        return True  # no keywords defined → always brand mode (Coin Hall, Meta Coin Guard, ChainReporter unaffected)
    text = (article.get('title', '') + ' ' + article.get('desc', '')).lower()
    return any(kw.lower() in text for kw in keywords)


def _fallback_brief(article, profile):
    title = (article.get('title') or '').strip()
    max_words = profile.get('headline_max_words', 6)
    headline = ' '.join(title.split()[:max_words])
    if profile.get('headline_uppercase', True):
        headline = headline.upper()
    brief = dict(profile['fallback_brief'])
    if headline:
        brief['headline'] = headline
    return brief


def validate_brief(brief, article, profile, recent=()):
    if not isinstance(brief, dict):
        return _fallback_brief(article, profile)

    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    families = _active_families(profile)
    axes = profile['axes']
    max_words = profile.get('headline_max_words', 6)

    family = brief.get('family')
    if family not in families:
        return _fallback_brief(article, profile)
    fam = families[family]
    uppercase = fam.get('headline_uppercase', profile.get('headline_uppercase', True))

    headline = (brief.get('headline') or '').strip()
    if not headline:
        return _fallback_brief(article, profile)
    words = headline.split()
    if len(words) > max_words:
        headline = ' '.join(words[:max_words])
    if uppercase:
        headline = headline.upper()

    subject_scene = (brief.get('subject_scene') or '').strip()
    lowered = subject_scene.lower()
    banned_terms = _BANNED_SUBJECT_TERMS + profile.get('extra_banned_subject_terms', [])
    if (not subject_scene or any(term in lowered for term in banned_terms)
            or _WALLET_ADDRESS_RE.search(subject_scene)):
        return _fallback_brief(article, profile)

    no_text_mode = profile.get('no_text_mode')
    if family == no_text_mode:
        art_style = (brief.get('art_style') or '').strip()
        recent_styles = {(r.get('art_style') or '').strip().lower() for r in recent[-5:]}
        if not art_style or art_style.lower() in recent_styles:
            return _fallback_brief(article, profile)

    data_elements = brief.get('data_elements') or []
    if not isinstance(data_elements, list):
        data_elements = []
    clean_elements = []
    max_len = fam.get('data_value_max_len')
    for el in data_elements:
        if isinstance(el, dict) and el.get('value'):
            value = str(el['value'])[:max_len] if max_len else str(el['value'])
            clean_elements.append({'value': value, 'label': str(el.get('label') or '')})
    data_elements = clean_elements[:fam['data_budget']]
    if family == no_text_mode:
        data_elements = []

    camera = brief.get(cam_axis)
    if camera not in axes[cam_axis]:
        camera = fam['default_axes'][cam_axis]

    energy = brief.get(nrg_axis)
    if energy not in axes[nrg_axis]:
        energy = fam['default_axes'][nrg_axis]

    env_restricted = profile.get('environment_restricted', {})
    environment = brief.get(env_axis)
    if environment not in axes[env_axis]:
        environment = fam['default_axes'][env_axis]
    elif environment in env_restricted:
        cond = env_restricted[environment]
        if energy not in cond.get('energies', []) and family not in cond.get('families', []):
            environment = fam['default_axes'][env_axis]

    mood_default = profile.get('mood_accent_default', next(iter(axes[mood_axis])))
    mood_restricted = profile.get('mood_accent_restricted', {})
    mood_accent = brief.get(mood_axis)
    if mood_accent not in axes[mood_axis]:
        mood_accent = mood_default
    elif mood_accent in mood_restricted:
        cond = mood_restricted[mood_accent]
        if isinstance(cond, str):
            cond = {'families': [cond]}
        if family not in cond.get('families', []) and environment not in cond.get('environments', []):
            mood_accent = mood_default

    companion = profile.get('axis_companion_field', {})
    if mood_accent in companion and not (brief.get(companion[mood_accent]) or '').strip():
        mood_accent = mood_default

    result = {
        'family': family,
        'headline': headline,
        'layout': 'art_with_data' if data_elements else 'art_only',
        'data_elements': data_elements,
        env_axis: environment,
        cam_axis: camera,
        nrg_axis: energy,
        mood_axis: mood_accent,
        'subject_scene': subject_scene,
    }

    axis_optional = profile.get('axis_optional', {})
    for axis in _extra_axes(profile):
        val = brief.get(axis)
        if axis_optional.get(axis):
            if val not in axes[axis] and val != 'none':
                val = 'none'
        else:
            if val not in axes[axis]:
                val = fam['default_axes'].get(axis, next(iter(axes[axis])))
        result[axis] = val

    # Cross-axis constraint: certain axis values are only valid in a specific family.
    for ax, constraints in profile.get('axis_family_required', {}).items():
        for restricted_val, required_family in constraints.items():
            if result.get(ax) == restricted_val and family != required_family:
                result[ax] = 'none' if axis_optional.get(ax) else fam['default_axes'].get(ax, next(iter(axes[ax])))

    for field in profile.get('passthrough_fields', []):
        result[field] = (brief.get(field) or '').strip()

    return result


# ── Stage 2b: deterministic prompt assembler ───────────────────────────────────
def _render_data_element(el, profile):
    label_part = ''
    if el.get('label'):
        label_tpl = profile.get('data_element_label_template', ' with the short label "{label}"')
        label_part = label_tpl.format(label=el['label'])
    return profile['data_element_template'].format(value=el['value'], label_part=label_part)


def assemble_prompt(brief, profile, brand_mode=True):
    fs = profile['frozen_style']
    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    fam = profile['families'][brief['family']]
    axes = profile['axes']

    parts = []

    # 1. Frozen style
    parts.append(
        f"{fs['format']}. {fs['palette']}. {fs['materials']}. {fs['rendering']}. "
        f"{fs['background_vocab']}. {fs['headline_zone']}."
    )

    # 2. Finish, if this profile has a finish axis
    if 'finish' in axes:
        parts.append(axes['finish'][brief['finish']])

    # 3. Environment
    parts.append(axes[env_axis][brief[env_axis]])

    # 4. Hall-theme injection, if set
    hall_theme = brief.get('hall_theme')
    if 'hall_theme' in axes and hall_theme not in (None, 'none'):
        parts.append(axes['hall_theme'][hall_theme])

    # 5. Subject
    subject_line = f"Subject: {brief['subject_scene']}"
    if brief.get('art_style'):
        subject_line += f" Art style: {brief['art_style']}."
    parts.append(subject_line)

    # 6. Family skeleton
    parts.append(fam['skeleton'])

    # 7. Data elements, if any
    if brief['data_elements']:
        tiles = '; '.join(_render_data_element(el, profile) for el in brief['data_elements'])
        parts.append(f"The scene also includes {tiles}.")

    # 7.5. Extra axes injected after data elements (e.g. wolf seal for RZ Prime)
    for ax in profile.get('axis_inject_after_data', []):
        val = brief.get(ax)
        if val and val != 'none':
            sentence = axes.get(ax, {}).get(val, '')
            if sentence:
                parts.append(sentence)

    # 8. Camera/composition + energy
    parts.append(axes[cam_axis][brief[cam_axis]] + ' ' + axes[nrg_axis][brief[nrg_axis]])

    # 9. Mood/accent
    parts.append(axes[mood_axis][brief[mood_axis]])

    # 10/11. Headline rule + legibility, or the no-text override
    if brief['family'] == profile.get('no_text_mode'):
        parts.append(f"{profile['no_text_line']} {fs['never']}.")
    else:
        headline_zone = (
            axes['headline_layout'][brief['headline_layout']] if 'headline_layout' in axes
            else fam.get('headline_treatment', fs['headline_zone'])
        )
        parts.append(f'Headline text: "{brief["headline"]}" -- {headline_zone}.')
        if brand_mode and profile.get('logo_line'):
            parts.append(profile['logo_line'])
        parts.append(f"{profile['legibility_line']} No other text anywhere in the image. {fs['never']}.")

    return ' '.join(parts)


def handle_promo_ideas(body):
    brand     = body.get('brand', '')
    prompt    = body.get('prompt', '').strip()
    model_key = body.get('modelKey', 'gpt')
    if not prompt:
        raise ValueError('prompt is required')
    pitch = BRAND_PROMO_PITCH.get(brand, '')
    sys_msg = (
        f"You are a social media content strategist for {brand}.\n"
        f"PRODUCT: {pitch}\n\n"
        "The user wants to create a promotional post. Based on their description, "
        "generate exactly 3 different post ideas. Each idea should have a different angle "
        "or hook — variety is key.\n\n"
        "Respond with a JSON array of 3 objects, each with:\n"
        '- "title": a short punchy headline (8-12 words, captures the post idea)\n'
        '- "description": a 1-2 sentence summary of what the post will communicate\n\n'
        "Respond with ONLY the JSON array, no other text."
    )
    user_msg = f"Create posts about: {prompt}"
    model_cfg = EDITORIAL_MODELS.get(model_key, EDITORIAL_MODELS['gpt'])
    model_id = model_cfg['id']
    msgs = [{'role': 'system', 'content': sys_msg}, {'role': 'user', 'content': user_msg}]
    raw = openrouter_chat(model_id, msgs, temperature=0.9, max_tokens=800)
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    ideas = json.loads(raw)
    if not isinstance(ideas, list):
        ideas = [ideas]
    return {'ideas': ideas[:3]}


def handle_generate_image(body):
    article   = body.get('article', {})
    platform  = body.get('platform', 'X')
    media     = body.get('mediaBrand', 'ChainReporter')
    sentiment = body.get('sentiment', 'Neutral')
    model     = body.get('model', 'openai/gpt-5.4-image-2')
    copy_text = body.get('copy', '')
    image_direction = body.get('imageDirection', '').strip()
    ref_images = body.get('referenceImages', []) or []

    profile = BRAND_IMAGE_PROFILES.get(media)
    brief = None
    if profile:
        recent     = _RECENT_BRIEFS.get(media, [])
        brand_mode = _article_mentions_brand(article, profile)
        raw_brief  = call_art_director(article, copy_text, sentiment, platform, profile, recent, brand_mode=brand_mode)
        brief      = validate_brief(raw_brief, article, profile, recent)
        if not brand_mode and 'wolf' in brief:
            brief['wolf'] = 'none'
        prompt = assemble_prompt(brief, profile, brand_mode=brand_mode)
        _remember_brief(media, brief, profile)
    else:
        # interim fallback for brands not yet migrated to the Art-Director pipeline
        tone = BRAND_VISUAL_TONE.get(media, 'premium crypto news, dark cinematic aesthetic')
        sent_tone = ('optimistic upward energy, green tones' if sentiment == 'Bullish'
                     else 'tense cautionary mood, red accents' if sentiment == 'Bearish'
                     else 'balanced neutral editorial')
        prompt = (
            f'Hyper-realistic editorial illustration for a premium crypto news brand. '
            f'Story: {article.get("title", "")}. Brand visual tone: {tone}. Mood: {sent_tone}. '
            f'Platform: {platform} post — {"square-friendly, bold visual" if platform == "Instagram" else "wide cinematic banner"}. '
            f'No text overlays. No logos.'
        )

    if image_direction:
        prompt = prompt + ' ' + image_direction

    print(f'[image] brief: {brief}', file=sys.stderr)
    print(f'[image] prompt: {prompt}', file=sys.stderr)
    image_b64 = openrouter_image(prompt, model, ref_images=ref_images or None)
    result = {'imageB64': image_b64, 'prompt': prompt, 'model': model}
    if brief is not None:
        result['brief'] = brief
    return result


def handle_sheets(action, body):
    payload = {'action': action, **body}
    if action == 'uploadImage' and 'driveFolder' not in payload and DRIVE_FOLDER_URL:
        payload['driveFolder'] = DRIVE_FOLDER_URL
    return call_apps_script(payload)


BATCH_WINDOW = _timedelta(minutes=10)
VALID_ACTIONS = {'approved', 'scheduled'}


def group_activity(rows):
    """rows: list[dict] ordered created_at DESC (most recent first).
    Returns list of batch dicts, most-recent-first."""
    batches = []
    for row in rows:
        ts = _datetime.fromisoformat(row['created_at'])
        last = batches[-1] if batches else None
        same_group = (
            last is not None and
            row['brand'] == last['brand'] and
            row['model_display'] == last['model_display'] and
            (last['_first_ts'] - ts) <= BATCH_WINDOW
        )
        if same_group:
            last['count'] += 1
            last['platforms'].add(row['platform'])
            last['actions'].add(row['action'])
        else:
            batches.append({
                'brand': row['brand'], 'model_display': row['model_display'],
                'count': 1, 'platforms': {row['platform']}, 'actions': {row['action']},
                'headline': row['headline'], 'created_at': row['created_at'], '_first_ts': ts,
            })
    return [{
        'brand': b['brand'], 'modelDisplay': b['model_display'], 'count': b['count'],
        'platforms': sorted(b['platforms']), 'actions': sorted(b['actions']),
        'headline': b['headline'], 'createdAt': b['created_at'],
    } for b in batches]


def build_account_summary(user_id):
    posts_generated = database.count_activity(user_id)
    scheduled       = database.count_activity(user_id, action='scheduled')
    saved_count     = database.count_saved_cards(user_id, status='saved')

    brand_stats = database.get_brand_stats(user_id)
    posts_by_brand = {b: brand_stats.get(b, {'generated': 0, 'scheduled': 0}) for b in MEDIA_LIST}

    recent_rows = database.get_recent_activity(user_id, limit=200)
    activity = group_activity(recent_rows)[:20]

    return {
        'stats': {'postsGenerated': posts_generated, 'scheduled': scheduled, 'saved': saved_count},
        'postsByBrand': posts_by_brand,
        'activity': activity,
        'recentKeywords': database.get_recent_keywords(user_id, limit=12),
    }


def handle_log_action(user_id, body):
    brand    = (body.get('brand') or '').strip()
    platform = (body.get('platform') or '').strip()
    model    = (body.get('modelDisplay') or '').strip()
    headline = (body.get('headline') or '').strip()
    action   = (body.get('action') or '').strip()
    if not brand or not platform or not action:
        raise ValueError('brand, platform, and action are required')
    if action not in VALID_ACTIONS:
        raise ValueError(f'Invalid action: {action}')
    database.log_activity(user_id, brand, platform, model, headline, action)
    return {'ok': True}


def handle_log_keywords(user_id, body):
    topics = body.get('topics', '')
    brands = body.get('brands', [])
    keywords = [k.strip() for k in topics.split(',') if k.strip()]
    for brand in (brands or ['']):
        database.log_keywords(user_id, keywords, brand)
    return {'ok': True, 'logged': len(keywords)}


def handle_brand_keywords(user_id, brands_param):
    brands = [b.strip() for b in brands_param.split(',') if b.strip()]
    if not brands:
        return {'keywords': []}
    return {'keywords': database.get_brand_keywords(user_id, brands)}


def handle_saved_discard(user_id, body):
    saved_id = body.get('id')
    if not saved_id:
        raise ValueError('id is required')
    if not database.update_saved_card_status(saved_id, user_id, 'discarded'):
        raise ValueError('Saved card not found')
    return {'ok': True}


def handle_saved_confirm_schedule(user_id, body):
    saved_id   = body.get('id')
    sched_date = body.get('scheduledDate')
    sched_time = body.get('scheduledTime')
    if not saved_id or not sched_date or not sched_time:
        raise ValueError('id, scheduledDate, and scheduledTime are required')

    card = database.get_saved_card(saved_id, user_id)
    if not card:
        raise ValueError('Saved card not found')

    copy = body.get('copy') or card['copy']
    hashtags = body.get('hashtags') or card['hashtags']

    call_apps_script({
        'action': 'schedule', 'id': card['card_id'], 'title': card['headline'],
        'source': card['source'], 'sourceUrl': card['source_link'] or '',
        'mediaBrand': card['brand'], 'platform': card['platform'], 'copy': copy,
        'hashtags': hashtags, 'sentiment': card['sentiment'],
        'fitScore': card['suitability'], 'impactScore': card['impact'], 'viralityScore': card['virality'],
        'scheduledDate': sched_date, 'scheduledTime': sched_time,
    })

    database.log_activity(user_id, card['brand'], card['platform'], card['model_display'], card['headline'], 'scheduled')
    database.update_saved_card_status(saved_id, user_id, 'scheduled')
    return {'ok': True}


def handle_schedule_create(user_id, body):
    scheduled_at = body.get('scheduledAt')
    if not scheduled_at:
        raise ValueError('scheduledAt is required')
    try:
        dt = _parse_iso_utc(scheduled_at)
    except ValueError:
        raise ValueError('Invalid scheduledAt')
    data = {**body, 'scheduledAt': dt.isoformat()}
    post_id = database.create_scheduled_post(user_id, data)
    return {'ok': True, 'id': post_id}


def handle_schedule_list(user_id):
    posts = database.get_scheduled_posts(user_id)
    for p in posts:
        p['has_image'] = bool(p.pop('image_b64', None))
    return {'posts': posts}


def handle_schedule_cancel(user_id, body):
    post_id = body.get('id')
    if not post_id:
        raise ValueError('id is required')
    row = database.cancel_scheduled_post(post_id, user_id)
    if not row:
        raise ValueError('Scheduled post not found or already processed')
    if row.get('saved_card_id'):
        database.update_saved_card_status(row['saved_card_id'], user_id, 'saved')
    return {'ok': True}


def handle_schedule_reschedule(user_id, body):
    post_id = body.get('id')
    scheduled_at = body.get('scheduledAt')
    if not post_id or not scheduled_at:
        raise ValueError('id and scheduledAt are required')
    try:
        dt = _parse_iso_utc(scheduled_at)
    except ValueError:
        raise ValueError('Invalid scheduledAt')
    if not database.reschedule_scheduled_post(post_id, user_id, dt.isoformat()):
        raise ValueError('Scheduled post not found or already processed')
    return {'ok': True}


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
    if hashtag_line:
        # The AI-generated copy often already ends with its own hashtags (e.g. folded into a
        # "Source: ... · #Tag1 #Tag2" line) — strip a trailing run so they aren't duplicated.
        copy_text = re.sub(r'\s*[·\-—|:]?\s*(?:#\w+\s*)+$', '', copy_text)
    source_line  = f'\n\n[🔗 Read full story]({link})' if link and link != '#' else ''
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
        origin = self.headers.get('Origin')
        allow  = origin if (ORIGIN == '*' and origin) else ORIGIN
        self.send_header('Access-Control-Allow-Origin', allow)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Content-Encoding')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self._json({'ok': True})
        elif self.path == '/api/auth/me':
            user = auth.get_current_user(self)
            if user is None:
                self._error(401, 'Not authenticated')
            else:
                self._json({'user': user})
        elif self.path == '/api/account/summary':
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            self._json(build_account_summary(user['id']))
        elif self.path.startswith('/api/account/brand-keywords'):
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(self.path).query)
            brands_param = params.get('brands', [''])[0]
            self._json(handle_brand_keywords(user['id'], brands_param))
        elif self.path == '/api/account/saved':
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            self._json({'cards': database.get_saved_cards(user['id'], status='saved')})
        elif self.path == '/api/schedule/list':
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            self._json(handle_schedule_list(user['id']))
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
            if path == '/api/auth/login':
                identifier = (body.get('identifier') or '').strip()
                password   = body.get('password') or ''
                remember   = bool(body.get('rememberMe'))
                user = database.get_user_by_identifier(identifier) if identifier else None
                if not user or not auth.verify_password(password, user['password_hash']):
                    return self._error(401, 'Invalid username/email or password')
                ttl_days = database.SESSION_TTL_DAYS if remember else 1
                token = database.create_session(user['id'], ttl_days=ttl_days)
                self._json(
                    {'user': database.get_user_by_id(user['id'])},
                    extra_headers={'Set-Cookie': auth.make_session_cookie(token, COOKIE_SECURE, ttl_days=ttl_days, remember=remember)}
                )
            elif path == '/api/auth/logout':
                token = auth.get_session_token(self)
                if token:
                    database.delete_session(token)
                self._json({'ok': True}, extra_headers={'Set-Cookie': auth.make_clear_cookie(COOKIE_SECURE)})
            elif path == '/api/account/log-action':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_log_action(user['id'], body))
            elif path == '/api/account/log-keywords':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_log_keywords(user['id'], body))
            elif path == '/api/account/save':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json({'ok': True, 'id': database.create_saved_card(user['id'], body)})
            elif path == '/api/account/saved/discard':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_saved_discard(user['id'], body))
            elif path == '/api/account/saved/confirm-schedule':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_saved_confirm_schedule(user['id'], body))
            elif path == '/api/schedule/create':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_schedule_create(user['id'], body))
            elif path == '/api/schedule/cancel':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_schedule_cancel(user['id'], body))
            elif path == '/api/schedule/reschedule':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_schedule_reschedule(user['id'], body))
            elif path == '/api/copy/generate':
                self._json(handle_generate_copy(body))
            elif path == '/api/promo/generate-ideas':
                self._json(handle_promo_ideas(body))
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

    def _json(self, data, status=200, extra_headers=None):
        body = json.dumps(data, default=_json_default).encode()
        self.send_response(status)
        self.send_cors()
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
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


# ── Background scheduler (auto-posts scheduled X/Telegram posts) ───────────────
SCHEDULER_INTERVAL_SEC = 30


def execute_scheduled_post(row):
    platform = row['platform']
    image_b64 = row.get('image_b64') or ''
    hashtags = row.get('hashtags') or []
    try:
        if platform == 'Telegram':
            handle_telegram_post({
                'imageB64': image_b64, 'headline': row['headline'],
                'copy': row.get('copy') or '', 'hashtags': hashtags,
                'link': row.get('source_link') or '',
            })
        elif platform == 'X':
            handle_twitter_post({
                'imageB64': image_b64, 'copy': row.get('copy') or '',
                'hashtags': hashtags, 'platform': platform, 'mediaBrand': row['brand'],
            })
        else:
            raise ValueError(f'Auto-posting not supported for platform {platform}')

        if image_b64 or row.get('image_url'):
            try:
                call_apps_script({
                    'action': 'approve', 'id': row['card_id'], 'title': row['headline'],
                    'source': row.get('source') or '', 'sourceUrl': row.get('source_link') or '',
                    'mediaBrand': row['brand'], 'platform': platform, 'copy': row.get('copy') or '',
                    'hashtags': hashtags, 'sentiment': row.get('sentiment') or '',
                    'fitScore': row.get('suitability'), 'impactScore': row.get('impact'),
                    'viralityScore': row.get('virality'),
                    'imageStatus': 'Image Approved', 'imageUrl': row.get('image_url') or '',
                })
            except Exception as e:
                # Sheet update is best-effort — the post itself already succeeded —
                # but log it so a stale Sheet row is debuggable later.
                print(f'[scheduler] Sheet update failed for post {row["id"]}: {e}', file=sys.stderr)

        database.log_activity(row['user_id'], row['brand'], platform,
                               row.get('model_display') or '', row['headline'], 'published')
        database.mark_scheduled_post(row['id'], 'posted')
    except Exception as e:
        database.mark_scheduled_post(row['id'], 'failed', error=str(e)[:500])


def run_scheduler_loop():
    # Posts whose time passed while the server was offline still fire on the
    # next poll after restart ("fire late", never silently skipped) — there is
    # no grace-window cutoff. A "failed" post is terminal (no automatic retry);
    # the user must re-schedule it manually.
    while True:
        try:
            for row in database.get_due_scheduled_posts(_datetime.now(_timezone.utc).isoformat()):
                execute_scheduled_post(row)
        except Exception as e:
            print(f'[scheduler] {e}', file=sys.stderr)
        time.sleep(SCHEDULER_INTERVAL_SEC)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    database.init_db()
    if not OPENROUTER_KEY:
        print('[WARN] OPENROUTER_API_KEY not set — AI routes will fail', file=sys.stderr)
    if not SCRIPT_URL or SCRIPT_URL.startswith('PASTE_'):
        print('[WARN] GOOGLE_APPS_SCRIPT_URL not set — Sheets routes will fail', file=sys.stderr)

    threading.Thread(target=run_scheduler_loop, daemon=True).start()

    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    server.daemon_threads = True
    print(f'ChainReporter backend running at http://localhost:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
