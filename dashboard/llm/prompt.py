"""Prompts for the two classification steps. The taxonomy is data: nothing here names a category."""

from dashboard.taxonomy import CategoryEntry, Taxonomy

NONE_OPTION = "(ninguna)"

# Generic examples used while the user has taught the app little; only those whose categories exist are used.
STATIC_EXAMPLES = [
    ("Recibo Greenpeace Espana Nº Recibo 4327382473498", "Regalos", "Donativos (ONG)"),
    ("Recibo Comercializadora Regulada, Gas Power, Nº 123213213123", "Servicios básicos", "Calefacción o gas"),
    ("Bizum Enviado a Marta Comida", "Gastos diarios", "Comida"),
]

_CATEGORY_INTRO = """You are a finance expert categorizing Spanish bank movements.
Pick the single category that best fits the operation. Answer with JSON only.

Categories:
{categories}
"""

_SUBCATEGORY_INTRO = """You are a finance expert categorizing Spanish bank movements.
The operation belongs to the category "{category}". Pick the subcategory that best fits it, or "{none}" if
none of them fits. Answer with JSON only.

Subcategories of "{category}":
{subcategories}
"""


def _line(name: str, description: str) -> str:
    return f"- {name}: {description}" if description else f"- {name}"


def category_prompt(taxonomy: Taxonomy, examples: list[tuple[str, str]], concept: str) -> str:
    """`examples` are (concept, category). The category list comes first so Ollama can reuse its cache."""
    listing = "\n".join(_line(c.name, c.description) for c in taxonomy)
    parts = [_CATEGORY_INTRO.format(categories=listing)]
    if examples:
        parts.append("Examples:")
        parts.extend(f"operation: {text}\ncategory: {category}\n" for text, category in examples)
    parts.append(f"Now classify:\noperation: {concept}\ncategory:")
    return "\n".join(parts)


def subcategory_prompt(category: CategoryEntry, examples: list[tuple[str, str]], concept: str) -> str:
    """`examples` are (concept, subcategory) of operations already in this category."""
    listing = "\n".join(_line(s.name, s.description) for s in category.subcategories)
    parts = [_SUBCATEGORY_INTRO.format(category=category.name, none=NONE_OPTION, subcategories=listing)]
    if examples:
        parts.append("Examples:")
        parts.extend(f"operation: {text}\nsubcategory: {sub}\n" for text, sub in examples)
    parts.append(f"Now classify:\noperation: {concept}\nsubcategory:")
    return "\n".join(parts)
