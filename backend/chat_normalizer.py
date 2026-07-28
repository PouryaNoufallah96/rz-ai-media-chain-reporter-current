"""Conservative bilingual question normalization for the in-app chatbot."""
import re
import unicodedata

from chat_faq_data import FAQ_SEEDS


_PERSIAN_RE = re.compile(r'[\u0600-\u06ff]')
_DIACRITICS_RE = re.compile(r'[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]')
_TOKEN_RE = re.compile(r'[a-z0-9]+|[ء-يپچژگکی]+', re.IGNORECASE)
_PERSIAN_TRANSLATION = str.maketrans({
    'ي': 'ی', 'ى': 'ی', 'ئ': 'ی', 'ك': 'ک', 'ة': 'ه', 'ۀ': 'ه',
})

# These are reviewed product-name and speech-to-text variants. Phrase aliases are
# applied before fuzzy token correction so names remain intact.
_PHRASE_ALIASES = {
    'hwo': 'how',
    'are zee prime': 'rz prime',
    'ar zee prime': 'rz prime',
    'r z prime': 'rz prime',
    'coin hole': 'coin hall',
    'coin haul': 'coin hall',
    'chain reportar': 'chainreporter',
    'chain repoter': 'chainreporter',
    'meta coin gard': 'meta coin guard',
    'insta gram': 'instagram',
    'tele gram': 'telegram',
    'ار زد پرایم': 'rz prime',
    'آر زد پرایم': 'rz prime',
    'کوین هال': 'coin hall',
    'چین ریپورتر': 'chainreporter',
    'متا کوین گارد': 'meta coin guard',
    'اینستا گرام': 'instagram',
}

_EXTRA_VOCABULARY = {
    'account', 'analyze', 'article', 'brand', 'cache', 'caption', 'card',
    'chainreporter', 'chatbot', 'coin', 'content', 'copy', 'edit', 'faq',
    'generate', 'hashtag', 'headline', 'how', 'image', 'instagram', 'media',
    'multimedia', 'post', 'preview', 'publish', 'reporter', 'rss', 'save',
    'schedule', 'source', 'telegram', 'translate', 'translation', 'twitter',
}


def _base_normalize(value):
    text = unicodedata.normalize('NFKC', value or '').lower()
    text = text.translate(_PERSIAN_TRANSLATION)
    text = _DIACRITICS_RE.sub('', text).replace('\u0640', '').replace('\u200c', ' ')
    return ' '.join(_TOKEN_RE.findall(text))


def _vocabulary():
    terms = set(_EXTRA_VOCABULARY)
    for faq in FAQ_SEEDS:
        for value in (faq['question'], *faq.get('keywords', []), *faq.get('aliases', [])):
            terms.update(_TOKEN_RE.findall(_base_normalize(value)))
    return {term for term in terms if len(term) >= 3 and not term.isdigit()}


_VOCABULARY = _vocabulary()


def _damerau_levenshtein(left, right):
    """Return edit distance, counting an adjacent transposition as one edit."""
    rows = len(left) + 1
    cols = len(right) + 1
    matrix = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        matrix[i][0] = i
    for j in range(cols):
        matrix[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )
            if i > 1 and j > 1 and left[i - 1] == right[j - 2] and left[i - 2] == right[j - 1]:
                matrix[i][j] = min(matrix[i][j], matrix[i - 2][j - 2] + 1)
    return matrix[-1][-1]


def _max_distance(token):
    if len(token) <= 3:
        return 0
    if len(token) <= 7:
        return 1
    return 2


def _same_script(left, right):
    return bool(_PERSIAN_RE.search(left)) == bool(_PERSIAN_RE.search(right))


def _fuzzy_candidate(token):
    limit = _max_distance(token)
    if not limit or token in _VOCABULARY or token.isdigit():
        return None
    candidates = []
    for term in _VOCABULARY:
        if not _same_script(token, term) or token[0] != term[0]:
            continue
        if abs(len(token) - len(term)) > limit:
            continue
        distance = _damerau_levenshtein(token, term)
        if distance <= limit:
            candidates.append((distance, abs(len(token) - len(term)), term))
    if not candidates:
        return None
    candidates.sort()
    best = candidates[0]
    if len(candidates) > 1 and candidates[1][:2] == best[:2]:
        return None
    confidence = 'high' if best[0] == 1 else 'medium'
    return {'source': token, 'target': best[2], 'kind': 'typo', 'confidence': confidence}


def understand(message):
    """Return a safe local interpretation while retaining the original text."""
    original = message or ''
    normalized = _base_normalize(original)
    interpreted = normalized
    corrections = []

    for source in sorted(_PHRASE_ALIASES, key=len, reverse=True):
        pattern = rf'(?<!\w){re.escape(source)}(?!\w)'
        if not re.search(pattern, interpreted):
            continue
        target = _PHRASE_ALIASES[source]
        interpreted = re.sub(pattern, target, interpreted)
        corrections.append({
            'source': source, 'target': target, 'kind': 'phonetic',
            'confidence': 'high',
        })

    corrected_tokens = []
    for token in interpreted.split():
        correction = _fuzzy_candidate(token)
        if correction:
            corrected_tokens.append(correction['target'])
            corrections.append(correction)
        else:
            corrected_tokens.append(token)
    interpreted = ' '.join(corrected_tokens)

    confidence = 'none'
    if corrections:
        confidence = 'medium' if any(
            item['confidence'] == 'medium' for item in corrections
        ) else 'high'
    return {
        'original': original,
        'normalizedOriginal': normalized,
        'interpreted': interpreted,
        'language': 'fa' if _PERSIAN_RE.search(original) else 'en',
        'confidence': confidence,
        'corrections': corrections,
    }


def clarification_reply(understanding):
    interpreted = understanding.get('interpreted', '')
    if understanding.get('language') == 'fa':
        return f'منظور شما این بود: «{interpreted}»؟ لطفاً تأیید کنید یا پرسش را دوباره بنویسید.'
    return f'Did you mean: "{interpreted}"? Please confirm or rephrase your question.'
