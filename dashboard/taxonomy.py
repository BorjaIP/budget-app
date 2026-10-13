"""Categories and subcategories: the owner's defaults and the rules for any custom taxonomy.

The taxonomy lives in the database (see `database/taxonomy_repository.py`) and can be edited by the user.
`DEFAULT_TAXONOMY` is what a new database starts with and what "restore defaults" brings back.
Expenses store a category and, optionally, a subcategory. Without a valid subcategory an expense belongs to its
parent category; without a valid category it belongs to Otros / General.
"""

from dataclasses import dataclass, field

OTHERS = "Otros"
OTHERS_SUB = "General"
FALLBACK = (OTHERS, OTHERS_SUB)
NO_SUBCATEGORY = "Sin subcategoría"  # option shown in pickers; stored as no subcategory
MAX_NAME_LENGTH = 40
MAX_DESCRIPTION_LENGTH = 200

DEFAULT_TAXONOMY: dict[str, list[str]] = {
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


@dataclass
class SubEntry:
    name: str
    description: str = ""


@dataclass
class CategoryEntry:
    name: str
    description: str = ""
    subcategories: list[SubEntry] = field(default_factory=list)


Taxonomy = list[CategoryEntry]


def default_taxonomy() -> Taxonomy:
    return [
        CategoryEntry(name, subcategories=[SubEntry(sub) for sub in subs])
        for name, subs in DEFAULT_TAXONOMY.items()
    ]


def category_names(taxonomy: Taxonomy) -> list[str]:
    return [c.name for c in taxonomy]


def find_category(taxonomy: Taxonomy, name: str) -> CategoryEntry | None:
    return next((c for c in taxonomy if c.name == name), None)


def subcategory_names(taxonomy: Taxonomy, category: str) -> list[str]:
    entry = find_category(taxonomy, category)
    return [s.name for s in entry.subcategories] if entry else []


def normalize_pair(
    taxonomy: Taxonomy, category: str | None, subcategory: str | None
) -> tuple[str, str | None]:
    """Make a (category, subcategory) pair valid: unknown subcategory -> parent only, unknown category -> Otros."""
    entry = find_category(taxonomy, category or "")
    if entry is None:
        return FALLBACK
    if subcategory and any(s.name == subcategory for s in entry.subcategories):
        return entry.name, subcategory
    return entry.name, None


def clean_name(raw: str) -> str:
    """A name the user typed: trimmed, single-spaced, non-empty and short."""
    name = " ".join((raw or "").split())
    if not name:
        raise ValueError("El nombre no puede estar vacío")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"El nombre admite como máximo {MAX_NAME_LENGTH} caracteres")
    return name


def clean_description(raw: str) -> str:
    text = " ".join((raw or "").split())
    if len(text) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"La descripción admite como máximo {MAX_DESCRIPTION_LENGTH} caracteres")
    return text
