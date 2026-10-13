"""Similarity between bank concepts: find what the user already labeled that looks the same.

Character 3-grams weighted by inverse document frequency (TF-IDF) and compared with cosine
similarity. It needs no model, runs in microseconds, and tolerates typos, abbreviations and
the extra words banks add ("Pago Movil En ...").
"""

import math
from collections import Counter
from typing import Any

from dashboard.llm.merchant import _plain, merchant_key

SIMILAR_THRESHOLD = 0.85  # the best label must be at least this similar to reuse it without the model
RIVAL_THRESHOLD = 0.70  # ... and no other close label may disagree on the category


def _text(concept: str) -> str:
    return merchant_key(concept) or _plain(concept).strip()


def _grams(text: str) -> Counter:
    padded = f"  {text} "
    return Counter(padded[i : i + 3] for i in range(len(padded) - 2))


class SimilarityIndex:
    """TF-IDF character n-gram index over labeled concepts (dicts with a "concept" key)."""

    def __init__(self, labels: list[dict[str, Any]]):
        self.labels = labels
        counts = [_grams(_text(label["concept"])) for label in labels]
        frequency = Counter(gram for c in counts for gram in c)
        total = max(len(labels), 1)
        self._idf = {gram: math.log(1 + total / df) for gram, df in frequency.items()}
        self._vectors = [self._vector(c) for c in counts]

    def _vector(self, counts: Counter) -> dict[str, float]:
        default_idf = math.log(1 + len(self.labels))
        weights = {g: n * self._idf.get(g, default_idf) for g, n in counts.items()}
        norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
        return {g: w / norm for g, w in weights.items()}

    def search(self, concept: str, k: int = 3) -> list[tuple[float, dict[str, Any]]]:
        """The k labels most similar to `concept`, best first, as (cosine score, label)."""
        query = self._vector(_grams(_text(concept)))
        scored = []
        for label, vector in zip(self.labels, self._vectors):
            small, big = (query, vector) if len(query) < len(vector) else (vector, query)
            score = sum(w * big.get(g, 0.0) for g, w in small.items())
            if score > 0:
                scored.append((score, label))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:k]


def confident_match(results: list[tuple[float, dict[str, Any]]]) -> tuple[float, dict[str, Any]] | None:
    """The best label when it is very similar and no close rival disagrees; otherwise None."""
    if not results or results[0][0] < SIMILAR_THRESHOLD:
        return None
    best_score, best = results[0]
    for score, other in results[1:]:
        if score >= RIVAL_THRESHOLD and other["category"] != best["category"]:
            return None
    return best_score, best


def select_similar(
    concept: str,
    labels: list[dict[str, Any]],
    limit: int = 8,
    index: SimilarityIndex | None = None,
) -> list[dict[str, Any]]:
    """The `limit` most similar labels, least similar first so the closest sits next to the question.

    When fewer than `limit` labels look alike, the rest are the most confirmed ones.
    """
    if not labels:
        return []
    index = index or SimilarityIndex(labels)
    chosen = [label for _, label in index.search(concept, limit)]
    if len(chosen) < limit:
        rest = [label for label in labels if label not in chosen]
        rest.sort(key=lambda label: label.get("confirmations", 1), reverse=True)
        chosen.extend(rest[: limit - len(chosen)])
    return list(reversed(chosen))
