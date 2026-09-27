"""Layer 2: shortlist registry agents that look similar to a request.

Uses sentence-transformers if it is installed; otherwise a dependency-free TF-IDF
cosine. The shortlist only decides which agents the LLM judge looks at, so a
simple method is fine for a small registry.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from typing import List, Sequence, Tuple

_STOPWORDS = set(
    """a an and are as at be by for from has have in into is it its of on or that the
    this to with will my me i you your it's them they their then than can do does
    agent agents bot tool""".split()
)


# Map common synonyms onto one canonical term so TF-IDF can match them.
_SYNONYMS = {
    "mail": "email", "inbox": "email", "mailbox": "email", "outlook": "email",
    "digest": "summary", "gist": "summary", "summarize": "summary", "summarise": "summary",
    "summarizes": "summary", "recap": "summary", "overview": "summary",
    "todo": "action", "task": "action",
    "bill": "invoice", "receipt": "invoice",
    "cv": "resume", "candidate": "resume",
    "transcript": "meeting",
    "patient": "clinical", "medical": "clinical", "discharge": "clinical",
    "translate": "translation", "translates": "translation",
    "review": "feedback", "opinion": "sentiment", "tone": "sentiment",
}


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = []
    for w in words:
        if w in _STOPWORDS or len(w) < 2:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]  # crude plural stripping: "invoices" -> "invoice"
        out.append(_SYNONYMS.get(w, w))
    return out


def _tfidf_scores(query: str, docs: Sequence[str]) -> List[float]:
    tokenized = [_tokens(d) for d in docs]
    q_tokens = _tokens(query)
    n = len(docs) + 1
    df: Counter = Counter()
    for toks in tokenized + [q_tokens]:
        df.update(set(toks))

    def vec(toks: List[str]) -> dict:
        tf = Counter(toks)
        return {t: (c / len(toks)) * (math.log(n / df[t]) + 1) for t, c in tf.items()} if toks else {}

    def cos(a: dict, b: dict) -> float:
        dot = sum(v * b.get(k, 0.0) for k, v in a.items())
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    qv = vec(q_tokens)
    return [cos(qv, vec(t)) for t in tokenized]


@lru_cache(maxsize=1)
def _st_model():
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def method_name() -> str:
    return "sentence-transformers" if _st_model() is not None else "TF-IDF"


def rank(query: str, docs: Sequence[str]) -> List[Tuple[int, float]]:
    """Return (doc_index, score 0..1) sorted best-first."""
    if not docs:
        return []
    model = _st_model()
    if model is not None:
        emb = model.encode([query, *docs], normalize_embeddings=True)
        scores = [float(max(0.0, (emb[0] * e).sum())) for e in emb[1:]]
    else:
        scores = _tfidf_scores(query, docs)
    return sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
