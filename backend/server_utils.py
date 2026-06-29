"""Shared server-side helpers: JSON serialization + ISO-timestamp parsing."""
from datetime import datetime as _datetime, date as _date, timezone as _timezone


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
