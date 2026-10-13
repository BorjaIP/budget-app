import logging
import math
import re
import time
from typing import Any

import httpx

from dashboard.config import settings

from .prompt import PROMPT, STATIC_EXAMPLES
from .retrieval import select_similar

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen2.5:3b-instruct"


CATEGORY_TAXONOMY: dict[str, list[str]] = {
    "Deuda": ["Tarjetas de crédito", "Préstamo caldera", "Otros préstamos", "Otros"],
    "Educación": ["Cursos", "Clases de música", "Otros"],
    "Ocio": [
        "Libros",
        "Conciertos o espectáculos",
        "Actividades al aire libre",
        "Fotografía",
        "Deporte",
        "Cine o teatro",
        "Otros",
    ],
    "Gastos diarios": [
        "Comida",
        "Restaurantes",
        "Comida domicilio",
        "Higiene personal",
        "Ropa",
        "Lavandería o tintorería",
        "Peluquería o belleza",
        "Suscripciones",
        "Otros",
    ],
    "Regalos": ["Regalos", "Donativos (ONG)", "Otros"],
    "Salud/médicos": [
        "Médicos (dentista/oculista)",
        "Especialistas",
        "Farmacia",
        "Urgencias",
        "Otros",
    ],
    "Vivienda": [
        "Alquiler o hipoteca",
        "Impuestos a la propiedad",
        "Muebles",
        "Artículos para el hogar",
        "Mantenimiento",
        "Mejoras",
        "Mudanza",
        "Otros",
    ],
    "Tecnología": [
        "Dominios y alojamiento",
        "Servicios online",
        "Hardware",
        "Software",
        "Otros",
    ],
    "Transporte": ["Combustible", "Transporte público", "Taxi/Uber", "Otros"],
    "Viajes": ["Billetes de avión", "Hoteles", "Comida", "Transporte", "Ocio", "Otros"],
    "Servicios básicos": ["Internet", "Electricidad", "Calefacción o gas", "Otros"],
    "Otros": ["General"],
}


_SUBCATEGORY_TO_CATEGORY: dict[str, str] = {}
for _cat, _subs in CATEGORY_TAXONOMY.items():
    for _sub in _subs:
        _SUBCATEGORY_TO_CATEGORY.setdefault(_sub, _cat)


_BRACKET_RE = re.compile(r"\[([^\[\]]+)\]")

_FALLBACK = ("Otros", "General")

def _ollama_base_url() -> str:
    return settings.ollama_base_url


def _is_valid_category(category: str, subcategory: str) -> bool:
    subs = CATEGORY_TAXONOMY.get(category)
    return subs is not None and subcategory in subs


def parse_category_response(raw: str) -> tuple[str, str]:
    """Extract (category, subcategory) from an LLM response.

    The model is expected to return two bracketed tags in order, e.g.
    '[Comida][Restaurantes]' (category, subcategory). Defensively also
    handles a single bracket (treated as a subcategory, mapped to its parent
    category) or garbage output. Returns ('Otros', 'General') whenever the
    parsed pair does not validate against CATEGORY_TAXONOMY.
    """
    if not raw:
        return _FALLBACK

    matches = [m.strip() for m in _BRACKET_RE.findall(raw) if m.strip()]
    if not matches:
        return _FALLBACK

    if len(matches) == 1:
        tag = matches[0]
        if tag in CATEGORY_TAXONOMY:
            # Tag matches a top-level category name: use its first subcategory.
            return (tag, CATEGORY_TAXONOMY[tag][0])
        cat = _SUBCATEGORY_TO_CATEGORY.get(tag)
        if cat is None:
            return _FALLBACK
        return (cat, tag) if _is_valid_category(cat, tag) else _FALLBACK

    cat, sub = matches[0], matches[1]
    if not _is_valid_category(cat, sub):
        return _FALLBACK
    return (cat, sub)


def build_few_shot_examples(rows: list[dict[str, Any]], limit: int = 8, diverse: bool = True) -> str:
    """Build the '{examples}' prompt block from manually-tagged expense rows.

    Each row must provide 'concept', 'category', 'subcategory' keys. Only
    rows whose category/subcategory validate against CATEGORY_TAXONOMY are
    used, up to `limit`, preferring one per distinct category. Falls back to
    the static hardcoded examples when fewer than 3 valid rows are available.
    """
    valid_rows = [
        row
        for row in rows
        if row.get("concept")
        and _is_valid_category(row.get("category", ""), row.get("subcategory", ""))
    ]

    if len(valid_rows) < 3:
        return STATIC_EXAMPLES

    if not diverse:  # rows are already ranked by similarity: keep their order
        selected = valid_rows[-limit:]
        lines = ["Examples:"]
        for row in selected:
            lines.append(f"operation: {row['concept']}")
            lines.append(f"→ [{row['category']}][{row['subcategory']}]")
            lines.append("")
        return "\n".join(lines).rstrip()

    seen_categories: set[str] = set()
    selected: list[dict[str, Any]] = []
    for row in valid_rows:
        if row["category"] in seen_categories:
            continue
        seen_categories.add(row["category"])
        selected.append(row)
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for row in valid_rows:
            if row in selected:
                continue
            selected.append(row)
            if len(selected) >= limit:
                break

    lines = ["Examples:"]
    for row in selected:
        lines.append(f"operation: {row['concept']}")
        lines.append(f"→ [{row['category']}][{row['subcategory']}]")
        lines.append("")
    return "\n".join(lines).rstrip()


def _get_dynamic_examples(concept: str = "", limit: int = 8) -> str:
    """Examples from what the user taught the app: the labels most similar to `concept`."""
    try:
        from dashboard.database.operations import db_manager

        labels = db_manager.get_merchant_labels()
        if len(labels) >= 3:
            return build_few_shot_examples(select_similar(concept, labels, limit), limit, diverse=False)
        rows = db_manager.get_manually_tagged_examples(limit=limit)
    except Exception:
        return STATIC_EXAMPLES
    return build_few_shot_examples(rows, limit=limit)


def bracket_confidence(tokens: list[dict] | None) -> float | None:
    """Joint probability the model gave to the two `[Category][Subcategory]` tags it answered.

    `tokens` is Ollama's `logprobs` list ({"token", "logprob"}); only tokens that open or sit
    inside the first two bracket pairs count. None when the answer has no brackets.
    """
    if not tokens:
        return None
    depth, closed, total, seen = 0, 0, 0.0, False
    for entry in tokens:
        text, logprob = entry["token"], entry["logprob"]
        if depth > 0 or "[" in text:
            total += logprob
            seen = True
        for ch in text:
            if ch == "[":
                depth += 1
            elif ch == "]" and depth > 0:
                depth -= 1
                closed += 1
        if closed >= 2:
            break
    return math.exp(total) if seen else None


async def query_llm_detailed(
    prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 180.0,
) -> dict:
    """Answer plus token log-probabilities. Temperature 0 so the same input gives the same answer."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{_ollama_base_url()}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "logprobs": True,
                "options": {"temperature": 0.0, "seed": 42, "num_predict": 48},
            },
        )
        response.raise_for_status()
        return response.json()


async def query_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 180.0,
) -> str:
    return (await query_llm_detailed(prompt, model=model, timeout=timeout)).get("response", "")


async def categorize_with_confidence(
    concept: str, model: str = DEFAULT_MODEL
) -> tuple[str, str, float | None]:
    """(category, subcategory, confidence). Confidence is 0 when the answer fell back to Otros/General."""
    examples = _get_dynamic_examples(concept)
    formatted_prompt = PROMPT.format(examples=examples, variable=concept)
    started = time.perf_counter()
    answer = await query_llm_detailed(formatted_prompt, model=model)
    raw = answer.get("response", "")
    result = parse_category_response(raw)
    confidence = bracket_confidence(answer.get("logprobs"))
    elapsed_ms = (time.perf_counter() - started) * 1000
    # Concepts and model answers come from bank data: only logged at DEBUG.
    logger.debug(
        "categorized %r -> %s (raw %r, confidence %s, %.0f ms)", concept, result, raw[:120], confidence, elapsed_ms
    )
    if result == _FALLBACK:
        logger.warning(
            "Result is Otros/General: the answer did not match the taxonomy or the model chose it (%.0f ms)",
            elapsed_ms,
        )
    return result[0], result[1], confidence


async def categorize_expense(concept: str, model: str = DEFAULT_MODEL) -> tuple[str, str]:
    category, subcategory, _ = await categorize_with_confidence(concept, model=model)
    return category, subcategory
