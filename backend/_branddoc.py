"""Brand-bible loader helper shared by copy & image handlers."""
import sys

from config import BRAND_PROMO_PITCH

try:
    import brand_docs as _brand_docs
    _BRAND_DOCS_AVAILABLE = True
except ImportError as _e3:
    print(f'[WARN] brand_docs package not available: {_e3}', file=sys.stderr)
    _BRAND_DOCS_AVAILABLE = False


def _brand_doc(brand):
    """Full brand-bible text for promo generation; falls back to the short BRAND_PROMO_PITCH blurb."""
    short = BRAND_PROMO_PITCH.get(brand, '')
    if _BRAND_DOCS_AVAILABLE:
        return _brand_docs.get_brand_doc(brand, fallback=short)
    return short
