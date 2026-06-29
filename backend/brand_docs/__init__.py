"""
Brand document loader — reads the full brand bibles (.docx) once at import time
and serves them from memory for promo content generation.

Files live next to this module:
    backend/brand_docs/RZ Prime.docx
    backend/brand_docs/Coin Hall.docx
    backend/brand_docs/Meta Coin Guard.docx

If a file is missing or unreadable, that brand falls back to the legacy short
BRAND_PROMO_PITCH blurb (passed in via get_brand_doc's fallback arg), so the
server never crashes on a bad doc. Every load outcome is logged to stderr.
"""
import sys
import threading
from pathlib import Path

try:
    from docx import Document  # python-docx
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

_HERE = Path(__file__).parent

# Brand display-name -> filename stem (matches the .docx filenames written by _convert.py)
_BRAND_FILES = {
    'RZ Prime':        'RZ Prime.docx',
    'Coin Hall':       'Coin Hall.docx',
    'Meta Coin Guard': 'Meta Coin Guard.docx',
}

_cache: dict[str, str] = {}
_loaded = False
_lock = threading.Lock()


def _read_docx(path: Path) -> str:
    """Extract plain text from a .docx, one paragraph per line (preserves blank-line spacing)."""
    doc = Document(str(path))
    return '\n'.join(p.text for p in doc.paragraphs)


def _load_all() -> None:
    """Populate _cache once. Safe to call from multiple threads."""
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        if not _DOCX_AVAILABLE:
            print('[brand_docs] python-docx not installed — promo will use short pitch fallbacks',
                  file=sys.stderr)
            _loaded = True
            return
        for brand, fname in _BRAND_FILES.items():
            path = _HERE / fname
            try:
                text = _read_docx(path)
                if text and text.strip():
                    _cache[brand] = text.strip()
                    print(f'[brand_docs] loaded brand doc: {brand} ({len(text)} chars)',
                          file=sys.stderr)
                else:
                    print(f'[brand_docs] WARNING {fname} is empty — {brand} uses fallback',
                          file=sys.stderr)
            except Exception as e:  # noqa: BLE001 — never let a bad doc crash the server
                print(f'[brand_docs] WARNING could not read {fname}: {e} — {brand} uses fallback',
                      file=sys.stderr)
        _loaded = True


def get_brand_doc(brand: str, fallback: str = '') -> str:
    """Return the full brand-bible text for a brand, or a short fallback if unavailable.

    `fallback` is the legacy short pitch (e.g. BRAND_PROMO_PITCH[brand]) so callers can
    always get *something* usable even if the .docx is missing.
    """
    if not _loaded:
        _load_all()
    return _cache.get(brand) or fallback


# Eagerly load at import so the startup log reflects doc availability immediately.
_load_all()
