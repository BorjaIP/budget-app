"""Does similarity search categorize your merchants correctly? Prints aggregates only.

Leave-one-out over the merchants you labeled by hand: each label is hidden in turn and predicted from
the others. Compares character n-gram TF-IDF (what the app uses) with embeddings from an Ollama model
when --embed-model is given. Never prints concepts, amounts or dates.

Usage: uv run python scripts/eval_similarity.py [--embed-model bge-m3] [--min-labels 20]
"""

import argparse
import math
import sys
from collections import defaultdict

import httpx

from dashboard.config import settings
from dashboard.database.operations import db_manager
from dashboard.llm.merchant import merchant_key
from dashboard.llm.retrieval import SimilarityIndex

BINS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.01)]


def _embed(model: str, texts: list[str]) -> list[list[float]]:
    response = httpx.post(
        f"{settings.ollama_base_url}/api/embed", json={"model": model, "input": texts}, timeout=300
    )
    response.raise_for_status()
    return response.json()["embeddings"]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / ((math.sqrt(sum(x * x for x in a)) or 1.0) * (math.sqrt(sum(y * y for y in b)) or 1.0))


def _report(name: str, outcomes: list[tuple[float, bool]]) -> None:
    total = len(outcomes)
    correct = sum(ok for _, ok in outcomes)
    print(f"\n{name}: {correct}/{total} right ({correct / total * 100:.1f} %) with the nearest label's category")
    for low, high in BINS:
        bucket = [ok for score, ok in outcomes if low <= score < high]
        if bucket:
            print(f"  similarity {low:.2f}-{min(high, 1.0):.2f}: {len(bucket):4d} cases, {sum(bucket) / len(bucket) * 100:5.1f} % right")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed-model", help="Ollama embedding model to compare, e.g. bge-m3")
    parser.add_argument("--min-labels", type=int, default=20)
    args = parser.parse_args()

    labels = db_manager.get_merchant_labels()
    print(f"hand-labeled merchants: {len(labels)}")
    if len(labels) < args.min_labels:
        sys.exit(f"need at least {args.min_labels} labeled merchants for a meaningful test; correct more by hand first")

    lexical = []
    for i, held_out in enumerate(labels):
        rest = labels[:i] + labels[i + 1 :]
        best = SimilarityIndex(rest).search(held_out["concept"], 1)
        score, nearest = best[0] if best else (0.0, {"category": None})
        lexical.append((score, nearest["category"] == held_out["category"]))
    _report("character n-gram TF-IDF", lexical)

    if args.embed_model:
        texts = [merchant_key(l["concept"]) or l["concept"] for l in labels]
        vectors = _embed(args.embed_model, texts)
        semantic = []
        for i, held_out in enumerate(labels):
            scored = [(_cosine(vectors[i], vectors[j]), labels[j]) for j in range(len(labels)) if j != i]
            score, nearest = max(scored, key=lambda pair: pair[0])
            semantic.append((score, nearest["category"] == held_out["category"]))
        _report(f"embeddings ({args.embed_model})", semantic)
        agree = sum(a[1] == b[1] for a, b in zip(lexical, semantic))
        print(f"\nboth methods right or both wrong on {agree}/{len(labels)} merchants")

    by_category = defaultdict(int)
    for label in labels:
        by_category[label["category"]] += 1
    print(f"categories with at least one label: {len(by_category)}")


if __name__ == "__main__":
    main()
