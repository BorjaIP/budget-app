"""Local model access and the two-step categorization (category, then subcategory).

Both steps use Ollama structured outputs: the answer is constrained to the names that exist in the user's
taxonomy, so it is always valid and the prompt only lists names (step 1) or one category's subcategories (step 2).
That keeps the cost flat whether the user has 10 categories or 100.
"""

import json
import logging
import math
import time
from typing import Any

import httpx

from dashboard.config import settings
from dashboard.taxonomy import FALLBACK, CategoryEntry, Taxonomy, find_category, for_amount

from .prompt import NONE_OPTION, STATIC_EXAMPLES, category_prompt, subcategory_prompt
from .retrieval import SimilarityIndex
from .shortlist import shortlist

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen2.5:3b-instruct"
EXAMPLES_PER_STEP = 8
MAX_CONCEPT_LENGTH = 200
CONTEXT_TOKENS = 8192  # enough for a prompt that lists a hundred categories


def _ollama_base_url() -> str:
    return settings.ollama_base_url


def _schema(key: str, options: list[str]) -> dict:
    return {"type": "object", "properties": {key: {"type": "string", "enum": options}}, "required": [key]}


def value_confidence(response: str, tokens: list[dict] | None, key: str) -> float | None:
    """Probability the model gave to the string it answered under `key` in a JSON response.

    `tokens` is Ollama's `logprobs` list. Only tokens inside the value count; the forced JSON syntax is ignored.
    None when the tokens do not rebuild the response.
    """
    if not tokens or "".join(t["token"] for t in tokens) != response:
        return None
    try:
        value = json.loads(response)[key]
    except (ValueError, KeyError, TypeError):
        return None
    marker = response.find(f'"{key}"')
    start = response.find(f'"{value}"', marker if marker >= 0 else 0)
    if start < 0:
        return None
    start, end = start + 1, start + 1 + len(value)
    total, position, seen = 0.0, 0, False
    for entry in tokens:
        token_end = position + len(entry["token"])
        if position < end and token_end > start:
            total += entry["logprob"]
            seen = True
        position = token_end
    return math.exp(total) if seen else None


async def query_llm_detailed(
    prompt: str,
    model: str = DEFAULT_MODEL,
    schema: dict | None = None,
    timeout: float = 180.0,
) -> dict:
    """Answer plus token log-probabilities. Temperature 0 so the same input gives the same answer."""
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "logprobs": True,
        "options": {"temperature": 0.0, "seed": 42, "num_predict": 60, "num_ctx": CONTEXT_TOKENS},
    }
    if schema is not None:
        body["format"] = schema
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{_ollama_base_url()}/api/generate", json=body)
        response.raise_for_status()
        return response.json()


async def _choose(prompt: str, key: str, options: list[str], model: str) -> tuple[str | None, float | None]:
    """One constrained answer: (the option, its probability). (None, None) when it cannot be read."""
    answer = await query_llm_detailed(prompt, model=model, schema=_schema(key, options))
    raw = answer.get("response", "")
    try:
        chosen = json.loads(raw)[key]
    except (ValueError, KeyError, TypeError):
        return None, None
    if chosen not in options:
        return None, None
    return chosen, value_confidence(raw, answer.get("logprobs"), key)


def _valid_labels(labels: list[dict[str, Any]], taxonomy: Taxonomy) -> list[dict[str, Any]]:
    """Labels whose category still exists (their subcategory is checked per step)."""
    return [label for label in labels if find_category(taxonomy, label["category"]) is not None]


def _category_examples(
    concept: str, labels: list[dict[str, Any]], index: SimilarityIndex | None, taxonomy: Taxonomy
) -> list[tuple[str, str]]:
    """Most similar labeled movements as (concept, category), the closest last. Generic ones fill a small corpus."""
    usable = _valid_labels(labels, taxonomy)
    ranked = [label for _, label in (index or SimilarityIndex(labels)).search(concept, EXAMPLES_PER_STEP * 3)]
    ranked = [label for label in ranked if label in usable][:EXAMPLES_PER_STEP]
    examples = [(label["concept"], label["category"]) for label in reversed(ranked)]
    if len(usable) < 20:
        generic = [(text, cat) for text, cat, _ in STATIC_EXAMPLES if find_category(taxonomy, cat) is not None]
        examples = generic + examples
    return examples


def _subcategory_examples(
    concept: str, category: CategoryEntry, labels: list[dict[str, Any]], index: SimilarityIndex | None
) -> list[tuple[str, str]]:
    names = {s.name for s in category.subcategories}
    pool = (index or SimilarityIndex(labels)).search(concept, 60)
    chosen = [
        label
        for _, label in pool
        if label["category"] == category.name and label.get("subcategory") in names
    ][:EXAMPLES_PER_STEP]
    return [(label["concept"], label["subcategory"]) for label in reversed(chosen)]


async def categorize_with_confidence(
    concept: str,
    taxonomy: Taxonomy,
    model: str = DEFAULT_MODEL,
    labels: list[dict[str, Any]] | None = None,
    index: SimilarityIndex | None = None,
    amount: float | None = None,
) -> tuple[str, str | None, float | None]:
    """(category, subcategory or None, confidence) for a bank concept.

    With `amount`, only the categories of its kind are offered: income categories for a positive amount,
    expense categories otherwise (Otros is always available).

    Confidence is the product of the probability of each step. It is 0 when the model's answer could not be read
    and the result is the fallback (Otros / General).
    """
    labels = labels or []
    concept = concept[:MAX_CONCEPT_LENGTH]
    started = time.perf_counter()
    if amount is not None:
        taxonomy = for_amount(taxonomy, amount)
    if not taxonomy:
        return FALLBACK[0], FALLBACK[1], 0.0
    full_taxonomy = taxonomy
    taxonomy = shortlist(full_taxonomy, concept, labels, index)  # a long taxonomy is cut to what can fit
    names = [c.name for c in taxonomy]

    confidence: float | None = 1.0
    if len(names) == 1:
        category_name = names[0]
    else:
        prompt = category_prompt(taxonomy, _category_examples(concept, labels, index, taxonomy), concept)
        category_name, step = await _choose(prompt, "category", names, model)
        if category_name is None:
            logger.warning("The model answer could not be read; used Otros / General")
            return FALLBACK[0], FALLBACK[1], 0.0
        confidence = step

    category = find_category(full_taxonomy, category_name)
    subcategory: str | None = None
    if category and category.subcategories:
        options = [s.name for s in category.subcategories]
        if len(options) == 1:
            subcategory = options[0]
        else:
            prompt = subcategory_prompt(category, _subcategory_examples(concept, category, labels, index), concept)
            chosen, step = await _choose(prompt, "subcategory", [*options, NONE_OPTION], model)
            subcategory = None if chosen in (None, NONE_OPTION) else chosen
            if confidence is not None:
                confidence = None if step is None else confidence * step

    elapsed_ms = (time.perf_counter() - started) * 1000
    # Concepts come from bank data: only logged at DEBUG.
    logger.debug("categorized %r -> %s / %s (confidence %s, %.0f ms)", concept, category_name, subcategory, confidence, elapsed_ms)
    return category_name, subcategory, confidence
