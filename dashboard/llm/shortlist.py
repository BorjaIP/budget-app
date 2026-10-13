"""Offer the model only the categories that can plausibly fit, so a long taxonomy does not distract it.

With up to `CAP` categories everything is offered. Beyond that the shortlist is:
1. Otros (the fallback must always be possible);
2. the categories of the labeled movements most similar to the concept;
3. the categories the user has used most;
4. categories nobody has used yet whose name or description looks like the concept (so a brand new
   category can be chosen from its first movement, before it has any label).
"""

from collections import Counter
from typing import Any

from dashboard.llm.retrieval import SimilarityIndex
from dashboard.taxonomy import OTHERS, Taxonomy

CAP = 30
SIMILAR_LABELS = 20
UNUSED_MATCH = 0.25
MAX_UNUSED = 8


def shortlist(
    taxonomy: Taxonomy,
    concept: str,
    labels: list[dict[str, Any]],
    index: SimilarityIndex | None = None,
    cap: int = CAP,
) -> Taxonomy:
    """The taxonomy itself when it is small, otherwise at most `cap` categories in their original order."""
    if len(taxonomy) <= cap:
        return taxonomy
    known = {c.name for c in taxonomy}
    chosen: list[str] = [OTHERS] if OTHERS in known else []

    def add(name: str) -> None:
        if name in known and name not in chosen and len(chosen) < cap:
            chosen.append(name)

    if labels:
        for _, label in (index or SimilarityIndex(labels)).search(concept, SIMILAR_LABELS):
            add(label["category"])
        for name, _ in Counter(label["category"] for label in labels).most_common():
            add(name)

    unused = [c for c in taxonomy if c.name not in chosen]
    if unused:
        text_index = SimilarityIndex([{"concept": f"{c.name} {c.description}".strip(), "name": c.name} for c in unused])
        matches = [label["name"] for score, label in text_index.search(concept, MAX_UNUSED) if score >= UNUSED_MATCH]
        for name in matches:
            add(name)
    for category in taxonomy:  # room left: keep the user's own order
        add(category.name)
    return [c for c in taxonomy if c.name in chosen]
