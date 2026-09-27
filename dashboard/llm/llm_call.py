import os
import re
from typing import Any

import httpx

from .prompt import PROMPT, STATIC_EXAMPLES

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

_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


def _ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL)


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


def build_few_shot_examples(rows: list[dict[str, Any]], limit: int = 8) -> str:
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


def _get_dynamic_examples(limit: int = 8) -> str:
    try:
        from dashboard.database.operations import db_manager

        rows = db_manager.get_manually_tagged_examples(limit=limit)
    except Exception:
        return STATIC_EXAMPLES
    return build_few_shot_examples(rows, limit=limit)


async def query_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 60.0,
) -> str:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{_ollama_base_url()}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json().get("response", "")


async def categorize_expense(concept: str, model: str = DEFAULT_MODEL) -> tuple[str, str]:
    examples = _get_dynamic_examples()
    formatted_prompt = PROMPT.format(examples=examples, variable=concept)
    raw = await query_llm(formatted_prompt, model=model)
    return parse_category_response(raw)
