"""SQLite storage for approved chatbot FAQs, answer cache, and question stats."""
import json
import re
import sqlite3
import threading
import unicodedata
from datetime import datetime, timezone

import database
from chat_faq_data import FAQ_SEEDS as APPROVED_FAQ_SEEDS


_INIT_LOCK = threading.Lock()
_INITIALIZED_DB = None
_PERMANENT_EXPIRY = '9999-12-31T23:59:59+00:00'
_FAQ_MATCH_STOPWORDS = {
    'a', 'about', 'an', 'and', 'are', 'can', 'do', 'does', 'for', 'how', 'i', 'in',
    'is', 'it', 'me', 'my', 'of', 'on', 'or', 'the', 'this', 'to', 'what',
    'tell', 'where', 'which', 'with', 'you', 'your',
    'از', 'است', 'این', 'با', 'برای', 'به', 'چه', 'چگونه', 'چیست', 'در',
    'را', 'روی', 'من', 'می', 'و', 'یا', 'کجا', 'که',
}
_FAQ_CONTEXT_ONLY_PHRASES = {'rz prime', 'coin hall', 'meta coin guard'}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _supported_language(value):
    return 'fa' if value == 'fa' else 'en'


def normalize_question(value):
    text = unicodedata.normalize('NFKC', value or '').lower().strip()
    replacements = {
        'chain reporter': 'chainreporter',
        'rzprime': 'rz prime',
        'coinhall': 'coin hall',
        'metacoinguard': 'meta coin guard',
        'twitter': 'x',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[^\w\u0600-\u06ff]+', ' ', text, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', text).strip()


_LEGACY_FAQ_SEEDS = (
    {
        'question': 'What can the ChainReporter chatbot help with?',
        'aliases': [
            'What can the chatbot do?',
            'How can the assistant help me?',
            'What can I ask the chatbot?',
        ],
        'answer': (
            'The chatbot can answer questions about ChainReporter, RZ Prime, Coin Hall, '
            'Meta Coin Guard, active news cards, and documented workspace functions. It '
            'provides guidance but cannot click controls or perform actions for you.'
        ),
        'language': 'en',
    },
    {
        'question': 'Which platforms can ChainReporter publish to?',
        'aliases': [
            'Where can ChainReporter publish?',
            'What social platforms can the website post to?',
            'Can ChainReporter publish social posts?',
        ],
        'answer': (
            'ChainReporter can publish directly to Telegram and X. It can prepare Instagram '
            'content, but direct Instagram publishing is not currently available.'
        ),
        'language': 'en',
    },
    {
        'question': 'How do I analyze stories?',
        'aliases': [
            'How do I analyze news?',
            'How does the Analyze button work?',
            'How do I route articles to brands?',
        ],
        'answer': (
            'In Multimedia, choose the media brands, platforms, sources, and editorial models '
            'in the sidebar, then select Analyze. The editorial pipeline filters and routes '
            'the selected stories into the appropriate brand lanes.'
        ),
        'language': 'en',
    },
    {
        'question': 'How do I generate an image?',
        'aliases': [
            'Where do I create an image?',
            'How can I make an image for a news card?',
            'How does image generation work?',
        ],
        'answer': (
            'Open a news card in Multimedia, use its Preview panel, and select the image '
            'generation control. The website creates the image through its Art Director '
            'pipeline using the selected story and brand guidance.'
        ),
        'language': 'en',
    },
    {
        'question': 'How do I schedule content?',
        'aliases': [
            'How do I schedule a post?',
            'Where can I schedule a news card?',
            'How does scheduling work?',
        ],
        'answer': (
            'Open the card Preview panel, choose Schedule, and select the date and time. You '
            'can review scheduled content from the Account page.'
        ),
        'language': 'en',
    },
    {
        'question': 'ربات ChainReporter چه کمکی می‌کند؟',
        'aliases': [
            'چت بات چه کاری انجام می‌دهد؟',
            'از ربات چه سوالی می‌توانم بپرسم؟',
        ],
        'answer': (
            'این ربات فقط درباره ChainReporter، برندهای RZ Prime، Coin Hall و Meta Coin Guard، '
            'کارت خبر فعال و قابلیت‌های مستند وب‌سایت راهنمایی می‌کند. ربات نمی‌تواند کنترل‌های '
            'سایت را کلیک کند یا عملیات را به جای کاربر انجام دهد.'
        ),
        'language': 'fa',
    },
    {
        'question': 'چطور خبرها را تحلیل کنم؟',
        'aliases': [
            'دکمه تحلیل چطور کار می‌کند؟',
            'چطور مقاله‌ها را به برندها مسیردهی کنم؟',
        ],
        'answer': (
            'در بخش Multimedia برندها، پلتفرم‌ها، منابع و مدل‌های تحریریه را از نوار کناری '
            'انتخاب کنید و سپس Analyze را بزنید. سیستم خبرها را فیلتر و در مسیر برند مناسب قرار می‌دهد.'
        ),
        'language': 'fa',
    },
    {
        'question': 'چطور محتوا را زمان‌بندی کنم؟',
        'aliases': [
            'چطور یک پست را زمان‌بندی کنم؟',
            'زمان‌بندی کارت خبر چطور است؟',
        ],
        'answer': (
            'کارت خبر را در پنل Preview باز کنید، Schedule را انتخاب کنید و تاریخ و ساعت را '
            'مشخص کنید. محتوای زمان‌بندی‌شده در صفحه Account قابل مشاهده است.'
        ),
        'language': 'fa',
    },
    {
        'question': 'What is RZ Prime?',
        'aliases': ['What does RZ Prime do?', 'Tell me about RZ Prime'],
        'answer': (
            'RZ Prime is a token-reservation platform. Users can reserve token deals with '
            'zero upfront payment, keep funds unlocked, pay only if the price rises, and '
            'cancel without penalties. The process is enforced on-chain by smart contracts.'
        ),
        'language': 'en',
    },
    {
        'question': 'What is Coin Hall?',
        'aliases': ['What does Coin Hall do?', 'Tell me about Coin Hall'],
        'answer': (
            'Coin Hall is a tokenized real-world-asset deal platform. It presents time-limited '
            'deals involving assets such as jewelry, real estate, and cars, with quantities, '
            'end dates, and outcome history tracked on-chain.'
        ),
        'language': 'en',
    },
    {
        'question': 'What is Meta Coin Guard?',
        'aliases': ['What does Meta Coin Guard do?', 'Tell me about Meta Coin Guard'],
        'answer': (
            'Meta Coin Guard is an automated, non-custodial on-chain protection service for '
            'crypto token value. Its documented product uses cover plans and smart contracts '
            'to compensate qualifying token-value losses without a traditional claims process.'
        ),
        'language': 'en',
    },
    {
        'question': 'What is ChainReporter?',
        'aliases': ['What does ChainReporter cover?', 'Tell me about ChainReporter'],
        'answer': (
            'ChainReporter is a crypto news media outlet covering markets, security incidents, '
            'regulation, launches, listings, governance, protocol mechanics, and notable people. '
            'Its editorial approach emphasizes fast, credible coverage without hype or price promises.'
        ),
        'language': 'en',
    },
    {
        'question': 'Which media brand should cover security news?',
        'aliases': ['Which brand is for hacks?', 'Where should I route a crypto security story?'],
        'answer': (
            'Meta Coin Guard is the primary fit for crypto-security stories such as exploits, '
            'wallet threats, smart-contract risks, scams, and on-chain protection. ChainReporter '
            'can cover a major security incident when it is also broad market news.'
        ),
        'language': 'en',
    },
    {
        'question': 'Which media brand should cover mainstream crypto news?',
        'aliases': ['Which brand is for general crypto news?', 'Where should I route market and regulation news?'],
        'answer': (
            'ChainReporter is the primary fit for mainstream crypto and macro news, including '
            'markets, ETFs, regulation, exchanges, institutional activity, and major industry events.'
        ),
        'language': 'en',
    },
    {
        'question': 'How do I generate social copy?',
        'aliases': ['How do I create a caption?', 'How do I generate copy for a card?'],
        'answer': (
            'Open a routed news card, choose its target platform, and use the copy-generation '
            'control. ChainReporter creates platform-specific copy, variants, hashtags, and '
            'topic-appropriate formatting from the selected article.'
        ),
        'language': 'en',
    },
    {
        'question': 'How do I save a news card?',
        'aliases': ['Where are saved cards?', 'How do I save content for later?'],
        'answer': (
            'Open the card Preview panel and choose Save. Saved cards are available from the '
            'Account page, where they can be reviewed, updated, scheduled, or discarded.'
        ),
        'language': 'en',
    },
    {
        'question': 'How do I translate news cards?',
        'aliases': ['Can ChainReporter translate cards?', 'How does card translation work?'],
        'answer': (
            'Use the translation control for the selected cards and choose the target language. '
            'ChainReporter translates the card content while keeping the original editorial context.'
        ),
        'language': 'en',
    },
    {
        'question': 'What news sources can I use?',
        'aliases': ['How do sources work?', 'Can I use RSS and Telegram sources?'],
        'answer': (
            'The Multimedia workspace can use configured RSS news sources and selected public '
            'Telegram channels. Choose the sources in the sidebar before running Analyze.'
        ),
        'language': 'en',
    },
    {
        'question': 'What is available on the Account page?',
        'aliases': ['What does the Account section show?', 'Where can I see saved and scheduled posts?'],
        'answer': (
            'The Account page shows activity and generation statistics, posts by brand, recent '
            'keywords, saved cards, and scheduled content.'
        ),
        'language': 'en',
    },
    {
        'question': 'How long is chatbot history stored?',
        'aliases': ['When are chat messages deleted?', 'Does chatbot history expire?'],
        'answer': (
            'Chat messages are deleted after one hour without a new chat message. The inactivity '
            'timer resets whenever a new user or assistant message is stored.'
        ),
        'language': 'en',
    },
    {
        'question': 'How does the chatbot answer without AI tokens?',
        'aliases': ['What is a zero-token answer?', 'How does the chatbot cache answers?'],
        'answer': (
            'The chatbot checks its local scope policy, approved FAQ answers, and permanent '
            'context-aware answer cache before calling OpenRouter. FAQ and cache matches are '
            'returned immediately with no AI-token usage.'
        ),
        'language': 'en',
    },
    {
        'question': 'RZ Prime چیست؟',
        'aliases': ['RZ Prime چه کاری انجام می‌دهد؟', 'درباره RZ Prime توضیح بده'],
        'answer': (
            'RZ Prime یک پلتفرم رزرو توکن است. کاربر می‌تواند بدون پرداخت اولیه فرصت‌های توکن '
            'را رزرو کند، سرمایه خود را آزاد نگه دارد و فرایند را از طریق قرارداد هوشمند انجام دهد.'
        ),
        'language': 'fa',
    },
    {
        'question': 'Coin Hall چیست؟',
        'aliases': ['Coin Hall چه کاری انجام می‌دهد؟', 'درباره Coin Hall توضیح بده'],
        'answer': (
            'Coin Hall پلتفرمی برای فرصت‌های دارایی واقعی توکنیزه‌شده مانند جواهرات، املاک و '
            'خودرو است. هر فرصت زمان، تعداد و نتیجه مشخص دارد و سابقه نتیجه روی زنجیره ثبت می‌شود.'
        ),
        'language': 'fa',
    },
    {
        'question': 'Meta Coin Guard چیست؟',
        'aliases': ['Meta Coin Guard چه کاری انجام می‌دهد؟', 'درباره Meta Coin Guard توضیح بده'],
        'answer': (
            'Meta Coin Guard یک سرویس خودکار و غیرامانی برای حفاظت از ارزش توکن‌های رمزارزی است '
            'که از طرح‌های پوشش و قراردادهای هوشمند استفاده می‌کند.'
        ),
        'language': 'fa',
    },
    {
        'question': 'ChainReporter چیست؟',
        'aliases': ['ChainReporter چه اخباری را پوشش می‌دهد؟', 'درباره ChainReporter توضیح بده'],
        'answer': (
            'ChainReporter یک رسانه خبری رمزارز است که بازار، امنیت، مقررات، صرافی‌ها، راه‌اندازی‌ها، '
            'حاکمیت و رویدادهای مهم صنعت را با رویکرد سریع و معتبر پوشش می‌دهد.'
        ),
        'language': 'fa',
    },
    {
        'question': 'چطور برای کارت خبر تصویر بسازم؟',
        'aliases': ['تولید تصویر چطور کار می‌کند؟', 'تصویر خبر را از کجا بسازم؟'],
        'answer': (
            'کارت خبر را در پنل Preview باز کنید و کنترل تولید تصویر را انتخاب کنید. وب‌سایت با '
            'استفاده از خبر انتخاب‌شده و راهنمای برند، تصویر را از مسیر Art Director تولید می‌کند.'
        ),
        'language': 'fa',
    },
    {
        'question': 'چطور متن شبکه اجتماعی تولید کنم؟',
        'aliases': ['چطور کپشن بسازم؟', 'تولید متن کارت خبر چطور است؟'],
        'answer': (
            'کارت خبر و پلتفرم مقصد را انتخاب کنید و کنترل تولید متن را بزنید. سیستم متن، نسخه‌های '
            'جایگزین و هشتگ‌های متناسب با همان مقاله و پلتفرم را آماده می‌کند.'
        ),
        'language': 'fa',
    },
    {
        'question': 'پیام‌های چت چه زمانی حذف می‌شوند؟',
        'aliases': ['تاریخچه چت چقدر نگهداری می‌شود؟', 'آیا پیام‌های ربات حذف می‌شوند؟'],
        'answer': (
            'پیام‌های چت پس از یک ساعت نبود پیام جدید حذف می‌شوند. با ثبت هر پیام جدید، زمان یک‌ساعته از نو شروع می‌شود.'
        ),
        'language': 'fa',
    },
    {
        'question': 'پاسخ بدون توکن چگونه کار می‌کند؟',
        'aliases': ['کش پاسخ ربات چیست؟', 'چطور ربات بدون مصرف توکن پاسخ می‌دهد؟'],
        'answer': (
            'ربات ابتدا قوانین محلی، پاسخ‌های تاییدشده FAQ و حافظه دائمی پاسخ‌ها را بررسی می‌کند. '
            'اگر پاسخ مطابق برند و زبان پیدا شود، بدون فراخوانی OpenRouter نمایش داده می‌شود.'
        ),
        'language': 'fa',
    },
)

_LEGACY_FAQ_QUESTIONS = tuple(faq['question'] for faq in _LEGACY_FAQ_SEEDS)
_FAQ_SEEDS = APPROVED_FAQ_SEEDS


def _connect():
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout = 5000')
    return conn


def ensure_tables():
    global _INITIALIZED_DB
    db_key = str(database.DB_PATH.resolve())
    if _INITIALIZED_DB == db_key:
        return
    with _INIT_LOCK:
        if _INITIALIZED_DB == db_key:
            return
        conn = _connect()
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_faq (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_question TEXT NOT NULL,
                    normalized_question TEXT NOT NULL,
                    aliases_json TEXT NOT NULL DEFAULT '[]',
                    keywords_json TEXT NOT NULL DEFAULT '[]',
                    answer TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    brand TEXT NOT NULL DEFAULT '',
                    approved INTEGER NOT NULL DEFAULT 1,
                    active INTEGER NOT NULL DEFAULT 1,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    priority INTEGER NOT NULL DEFAULT 50,
                    managed_key TEXT,
                    last_used_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(normalized_question, language, brand)
                )
            ''')
            faq_columns = {
                row['name'] for row in conn.execute('PRAGMA table_info(chat_faq)').fetchall()
            }
            if 'keywords_json' not in faq_columns:
                conn.execute("ALTER TABLE chat_faq ADD COLUMN keywords_json TEXT NOT NULL DEFAULT '[]'")
            if 'priority' not in faq_columns:
                conn.execute('ALTER TABLE chat_faq ADD COLUMN priority INTEGER NOT NULL DEFAULT 50')
            if 'managed_key' not in faq_columns:
                conn.execute('ALTER TABLE chat_faq ADD COLUMN managed_key TEXT')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_answer_cache (
                    cache_key TEXT PRIMARY KEY,
                    normalized_question TEXT NOT NULL,
                    context_key TEXT NOT NULL,
                    language TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    knowledge_version TEXT NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_cache_expiry ON chat_answer_cache (expires_at)')
            # Migrate every existing temporary cache entry to permanent storage.
            conn.execute(
                'UPDATE chat_answer_cache SET expires_at = ? WHERE expires_at <> ?',
                (_PERMANENT_EXPIRY, _PERMANENT_EXPIRY),
            )
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_question_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_question TEXT NOT NULL,
                    example_question TEXT NOT NULL,
                    context_key TEXT NOT NULL,
                    language TEXT NOT NULL,
                    ask_count INTEGER NOT NULL DEFAULT 0,
                    ai_count INTEGER NOT NULL DEFAULT 0,
                    faq_hit_count INTEGER NOT NULL DEFAULT 0,
                    cache_hit_count INTEGER NOT NULL DEFAULT 0,
                    local_reply_count INTEGER NOT NULL DEFAULT 0,
                    last_source TEXT NOT NULL,
                    first_asked_at TEXT NOT NULL,
                    last_asked_at TEXT NOT NULL,
                    UNIQUE(normalized_question, context_key, language)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_term_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_term TEXT NOT NULL,
                    target_term TEXT NOT NULL,
                    language TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    seen_count INTEGER NOT NULL DEFAULT 1,
                    approved INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    UNIQUE(source_term, target_term, language)
                )
            ''')
            now = _now_iso()
            for legacy_question in _LEGACY_FAQ_QUESTIONS:
                conn.execute(
                    "UPDATE chat_faq SET managed_key = 'legacy' "
                    'WHERE normalized_question = ? AND managed_key IS NULL',
                    (normalize_question(legacy_question),),
                )
            conn.execute('UPDATE chat_faq SET active = 0 WHERE managed_key IS NOT NULL')
            for faq in _FAQ_SEEDS:
                conn.execute(
                    '''
                    INSERT INTO chat_faq
                    (canonical_question, normalized_question, aliases_json, keywords_json,
                     answer, language, brand, approved, active, priority, managed_key,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, '', 1, 1, ?, ?, ?, ?)
                    ON CONFLICT(normalized_question, language, brand) DO UPDATE SET
                        canonical_question = excluded.canonical_question,
                        aliases_json = excluded.aliases_json,
                        keywords_json = excluded.keywords_json,
                        answer = excluded.answer,
                        approved = 1,
                        active = 1,
                        priority = excluded.priority,
                        managed_key = excluded.managed_key,
                        updated_at = excluded.updated_at
                    ''',
                    (
                        faq['question'], normalize_question(faq['question']),
                        json.dumps(faq.get('aliases', []), ensure_ascii=False),
                        json.dumps(faq.get('keywords', []), ensure_ascii=False),
                        faq['answer'], faq['language'], faq.get('priority', 50),
                        faq['managedKey'], now, now,
                    ),
                )
            conn.commit()
            _INITIALIZED_DB = db_key
        finally:
            conn.close()


def find_faq(normalized_question, language, brand=''):
    ensure_tables()
    language = _supported_language(language)
    conn = _connect()
    try:
        rows = conn.execute(
            '''
            SELECT * FROM chat_faq
            WHERE active = 1 AND approved = 1 AND language = ? AND brand IN ('', ?)
            ORDER BY priority DESC, CASE WHEN brand = ? THEN 0 ELSE 1 END, id
            ''',
            (language, brand, brand),
        ).fetchall()
        question_tokens = sorted(normalized_question.split())
        question_set = set(question_tokens)
        significant_question_set = question_set - _FAQ_MATCH_STOPWORDS
        best = None
        for row in rows:
            candidates = [row['normalized_question']]
            candidates.extend(normalize_question(alias) for alias in json.loads(row['aliases_json'] or '[]'))
            if normalized_question in candidates or any(
                question_tokens and question_tokens == sorted(candidate.split())
                for candidate in candidates
            ):
                best = (float('inf'), row)
                break

            score = row['priority'] / 100.0
            matched_tokens = set()
            strong_phrase = False
            single_keyword_match = False
            for keyword in json.loads(row['keywords_json'] or '[]'):
                phrase = normalize_question(keyword)
                phrase_tokens = set(phrase.split())
                if not phrase_tokens:
                    continue
                significant_phrase_tokens = phrase_tokens - _FAQ_MATCH_STOPWORDS
                if phrase in _FAQ_CONTEXT_ONLY_PHRASES:
                    if significant_question_set == significant_phrase_tokens:
                        score += 6 + len(phrase_tokens)
                        strong_phrase = True
                    continue
                overlap = significant_question_set & significant_phrase_tokens
                matched_tokens.update(overlap)
                if (
                    len(significant_phrase_tokens) == 1
                    and significant_question_set == significant_phrase_tokens
                ):
                    single_keyword_match = True
                if phrase in normalized_question:
                    score += 6 + len(phrase_tokens)
                    strong_phrase = strong_phrase or len(phrase_tokens) >= 2
                else:
                    score += len(overlap)

            qualifies = strong_phrase or len(matched_tokens) >= 2 or single_keyword_match
            if qualifies and (best is None or score > best[0]):
                best = (score, row)

        if not best:
            return None
        row = best[1]
        conn.execute(
            'UPDATE chat_faq SET hit_count = hit_count + 1, last_used_at = ? WHERE id = ?',
            (_now_iso(), row['id']),
        )
        conn.commit()
        return {'id': row['id'], 'answer': row['answer']}
    finally:
        conn.close()


def get_cached_answer(cache_key, knowledge_version):
    ensure_tables()
    now = _now_iso()
    conn = _connect()
    try:
        row = conn.execute(
            'SELECT answer FROM chat_answer_cache WHERE cache_key = ? AND knowledge_version = ?',
            (cache_key, knowledge_version),
        ).fetchone()
        if not row:
            conn.commit()
            return None
        conn.execute(
            'UPDATE chat_answer_cache SET hit_count = hit_count + 1, updated_at = ? WHERE cache_key = ?',
            (now, cache_key),
        )
        conn.commit()
        return row['answer']
    finally:
        conn.close()


def save_cached_answer(cache_key, normalized_question, context_key, language, answer,
                       knowledge_version):
    ensure_tables()
    language = _supported_language(language)
    now = _now_iso()
    conn = _connect()
    try:
        conn.execute(
            '''
            INSERT INTO chat_answer_cache
            (cache_key, normalized_question, context_key, language, answer, knowledge_version,
             expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                answer = excluded.answer,
                knowledge_version = excluded.knowledge_version,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
            ''',
            (
                cache_key, normalized_question, context_key, language, answer,
                knowledge_version, _PERMANENT_EXPIRY, now, now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def record_question(normalized_question, example_question, context_key, language, source):
    ensure_tables()
    language = _supported_language(language)
    now = _now_iso()
    counters = {
        'ai': (1, 0, 0, 0),
        'faq': (0, 1, 0, 0),
        'cache': (0, 0, 1, 0),
        'local_policy': (0, 0, 0, 1),
    }
    ai, faq, cache, local = counters.get(source, (0, 0, 0, 1))
    conn = _connect()
    try:
        conn.execute(
            '''
            INSERT INTO chat_question_stats
            (normalized_question, example_question, context_key, language, ask_count,
             ai_count, faq_hit_count, cache_hit_count, local_reply_count, last_source,
             first_asked_at, last_asked_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(normalized_question, context_key, language) DO UPDATE SET
                example_question = excluded.example_question,
                ask_count = ask_count + 1,
                ai_count = ai_count + excluded.ai_count,
                faq_hit_count = faq_hit_count + excluded.faq_hit_count,
                cache_hit_count = cache_hit_count + excluded.cache_hit_count,
                local_reply_count = local_reply_count + excluded.local_reply_count,
                last_source = excluded.last_source,
                last_asked_at = excluded.last_asked_at
            ''',
            (
                normalized_question, example_question[:500], context_key, language,
                ai, faq, cache, local, source, now, now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def record_corrections(corrections, language):
    if not corrections:
        return
    ensure_tables()
    language = _supported_language(language)
    now = _now_iso()
    conn = _connect()
    try:
        for correction in corrections:
            conn.execute(
                '''
                INSERT INTO chat_term_corrections
                (source_term, target_term, language, kind, confidence, seen_count,
                 approved, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(source_term, target_term, language) DO UPDATE SET
                    kind = excluded.kind,
                    confidence = excluded.confidence,
                    seen_count = seen_count + 1,
                    last_seen_at = excluded.last_seen_at
                ''',
                (
                    correction['source'], correction['target'], language,
                    correction['kind'], correction['confidence'],
                    1 if correction['kind'] == 'phonetic' else 0, now, now,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def top_questions(limit=50):
    ensure_tables()
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT * FROM chat_question_stats ORDER BY ask_count DESC, last_asked_at DESC LIMIT ?',
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
