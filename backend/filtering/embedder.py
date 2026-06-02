import hashlib
import os
import pickle
import time
from pathlib import Path

import numpy as np
from openai import OpenAI

from .config import EMBED_BATCH

MODEL = 'text-embedding-3-small'
DIM   = 1536

# Anchor cache path to the backend/data/ directory regardless of CWD
_DEFAULT_CACHE = str(Path(__file__).parent.parent / 'data' / 'embed_cache.pkl')


def _l2(mat: np.ndarray) -> np.ndarray:
    mat = np.asarray(mat, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class Embedder:
    def __init__(self, cache_path: str = os.environ.get('EMBED_CACHE_PATH', _DEFAULT_CACHE)):
        self.client     = OpenAI()   # reads OPENAI_API_KEY from env
        self.batch_size = EMBED_BATCH
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.store: dict = {}
        if self.cache_path.exists():
            try:
                self.store = pickle.loads(self.cache_path.read_bytes())
            except Exception:
                self.store = {}

    def _key(self, text: str) -> str:
        return hashlib.sha1(f'{MODEL}\x00{text}'.encode()).hexdigest()

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(5):
            try:
                r = self.client.embeddings.create(model=MODEL, input=texts)
                return [d.embedding for d in r.data]
            except Exception as e:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, DIM), dtype=np.float32)

        out    = [None] * len(texts)
        miss_i = []
        miss_t = []

        for i, t in enumerate(texts):
            cached = self.store.get(self._key(t))
            if cached is None:
                miss_i.append(i)
                miss_t.append(t)
            else:
                out[i] = cached

        api_calls  = 0
        cache_hits = len(texts) - len(miss_t)

        for j in range(0, len(miss_t), self.batch_size):
            chunk = miss_t[j:j + self.batch_size]
            vecs  = _l2(self._call_api(chunk))
            api_calls += 1
            for k, vec in enumerate(vecs):
                idx = miss_i[j + k]
                out[idx] = vec
                self.store[self._key(miss_t[j + k])] = vec

        if miss_t:
            self.cache_path.write_bytes(pickle.dumps(self.store))

        return np.vstack(out).astype(np.float32), api_calls, cache_hits
