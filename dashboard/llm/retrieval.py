"""Pick the labeled examples most similar to a concept (retrieval-based in-context learning)."""

import math
import re
from collections import Counter
from typing import Any

from dashboard.llm.merchant import _plain


def _tokens(text: str) -> set[str]:
    return {t for t in re.sub(r"[^a-z ]+", " ", _plain(text)).split() if len(t) > 1}


def select_similar(
    concept: str, labels: list[dict[str, Any]], limit: int = 8
) -> list[dict[str, Any]]:
    """The `limit` labels sharing the most (rare) words with `concept`, least similar first.

    Words are weighted by inverse document frequency over the labels, so a shared merchant name
    counts more than a generic word. When fewer than `limit` labels share any word, the rest
    are the most confirmed ones. The closest example goes last, next to the question.
    """
    if not labels:
        return []
    docs = [_tokens(label["concept"]) for label in labels]
    frequency = Counter(token for doc in docs for token in doc)
    total = len(labels)

    def weight(token: str) -> float:
        return math.log(1 + total / frequency.get(token, 1))

    target = _tokens(concept)
    scored = []
    for label, doc in zip(labels, docs):
        shared = target & doc
        if not shared:
            continue
        union = target | doc
        score = sum(weight(t) for t in shared) / sum(weight(t) for t in union)
        scored.append((score, label))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    chosen = [label for _, label in scored[:limit]]

    if len(chosen) < limit:
        rest = [label for label in labels if label not in chosen]
        rest.sort(key=lambda label: label.get("confirmations", 1), reverse=True)
        chosen.extend(rest[: limit - len(chosen)])
    return list(reversed(chosen))
