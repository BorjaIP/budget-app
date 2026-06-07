import re

import httpx

from .prompt import PROMPT


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


def parse_category_response(raw: str) -> tuple[str, str]:
    """Extract (category, subcategory) from an LLM response.

    The model is expected to return one bracketed tag like '[Comida]'. We map
    the tag to its parent category. If the model emits two brackets we use
    them as (category, subcategory). Returns ('Otros', 'General') on failure.
    """
    if not raw:
        return ("Otros", "General")

    matches = [m.strip() for m in _BRACKET_RE.findall(raw) if m.strip()]
    if not matches:
        return ("Otros", "General")

    if len(matches) == 1:
        sub = matches[0]
        cat = _SUBCATEGORY_TO_CATEGORY.get(sub)
        if cat is None and sub in CATEGORY_TAXONOMY:
            return (sub, CATEGORY_TAXONOMY[sub][0])
        return (cat or "Otros", sub if cat else "General")

    cat, sub = matches[0], matches[1]
    if cat not in CATEGORY_TAXONOMY:
        cat = _SUBCATEGORY_TO_CATEGORY.get(cat, "Otros")
    return (cat, sub)


async def query_llm(
    prompt_template: str,
    variable: str,
    model: str = "mistral:7b-instruct-v0.2-q3_K_M",
    timeout: float = 60.0,
) -> str:
    formatted_prompt = prompt_template.format(variable=variable)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": formatted_prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json().get("response", "")


async def categorize_expense(
    concept: str, model: str = "mistral:7b-instruct-v0.2-q3_K_M"
) -> tuple[str, str]:
    raw = await query_llm(PROMPT, concept, model=model)
    return parse_category_response(raw)
