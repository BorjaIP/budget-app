"""Categories and subcategories: the owner's defaults and the rules for any custom taxonomy.

The taxonomy lives in the database (see `database/taxonomy_repository.py`) and can be edited by the user.
`DEFAULT_TAXONOMY` is what a new database starts with and what "restore defaults" brings back.
A category is either for expenses or for income, and a movement is classified among the categories of its own
kind (the sign of its amount decides); Otros is available to both. Expenses store a category and, optionally,
a subcategory. Without a valid subcategory an expense belongs to its
parent category; without a valid category it belongs to Otros / General.
"""

from dataclasses import dataclass, field

OTHERS = "Otros"
OTHERS_SUB = "General"
FALLBACK = (OTHERS, OTHERS_SUB)
KIND_EXPENSE = "expense"
KIND_INCOME = "income"
DEFAULT_INCOME_CATEGORIES = ["Nómina"]  # a new database starts with these income categories
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
    kind: str = KIND_EXPENSE


Taxonomy = list[CategoryEntry]


def default_taxonomy() -> Taxonomy:
    expenses = [
        CategoryEntry(name, subcategories=[SubEntry(sub) for sub in subs])
        for name, subs in DEFAULT_TAXONOMY.items()
    ]
    income = [CategoryEntry(name, kind=KIND_INCOME) for name in DEFAULT_INCOME_CATEGORIES]
    return [*expenses[:-1], *income, expenses[-1]]  # Otros stays last


def category_names(taxonomy: Taxonomy, kind: str | None = None) -> list[str]:
    """Names in order; with `kind`, only that kind (Otros, available to both, is always included)."""
    return [c.name for c in taxonomy if kind is None or c.kind == kind or c.name == OTHERS]


def kind_for_amount(amount: float) -> str:
    return KIND_INCOME if amount > 0 else KIND_EXPENSE


def for_amount(taxonomy: Taxonomy, amount: float) -> Taxonomy:
    """The categories a movement of this amount can have: its own kind plus Otros."""
    kind = kind_for_amount(amount)
    return [c for c in taxonomy if c.kind == kind or c.name == OTHERS]


def clean_kind(raw: str | None) -> str:
    if raw not in (KIND_EXPENSE, KIND_INCOME):
        raise ValueError("El tipo debe ser gasto o ingreso")
    return raw


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
