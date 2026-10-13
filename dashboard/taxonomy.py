"""Categories and subcategories: the owner's defaults and the rules for any custom taxonomy.

The taxonomy lives in the database (see `database/taxonomy_repository.py`) and can be edited by the user.
`DEFAULT_TAXONOMY` is what a new database starts with and what "restore defaults" brings back.
A category is for expenses, for income or for saving. A movement is classified among the categories of its own kind
(the sign of its amount decides), the saving ones and Otros, which are available to every movement. Saving
categories hold transfers to and from accounts the app does not see: they are neither spending nor income. Expenses store a category and, optionally,
a subcategory. Without a valid subcategory an expense belongs to its
parent category; without a valid category it belongs to Otros / General.
"""

from dataclasses import dataclass, field

OTHERS = "Otros"
OTHERS_SUB = "General"
FALLBACK = (OTHERS, OTHERS_SUB)
KIND_EXPENSE = "expense"
KIND_INCOME = "income"
KIND_SAVING = "saving"  # money moved to accounts the app does not see: neither spent nor earned
KINDS = (KIND_EXPENSE, KIND_INCOME, KIND_SAVING)
DEFAULT_INCOME_CATEGORIES = ["Nómina"]  # a new database starts with these income categories
DEFAULT_SAVING_CATEGORIES = {"Ahorro": ["Traspaso a cuenta de ahorro", "Retirada de ahorro"]}

# Short explanations sent to the model for the owner's categories (the user can edit them).
DEFAULT_DESCRIPTIONS = {
    "Deuda": "Pagos de deudas: tarjetas de crédito, préstamos y cuotas de financiación.",
    "Educación": "Cursos, clases y formación: academias, clases de música, matrículas y material.",
    "Ocio": "Tiempo libre: libros, conciertos, cine y teatro, deporte, fotografía y actividades al aire libre.",
    "Gastos diarios": "Gasto cotidiano: supermercado, restaurantes, comida a domicilio, ropa, higiene, peluquería, "
    "lavandería y suscripciones.",
    "Regalos": "Regalos a otras personas y donativos a ONG.",
    "Salud/médicos": "Salud: médicos, dentista, oculista, especialistas, farmacia y urgencias.",
    "Vivienda": "Casa: alquiler o hipoteca, impuestos del inmueble, muebles, hogar, mantenimiento, mejoras y mudanzas.",
    "Tecnología": "Tecnología: hardware, software, servicios online, dominios y alojamiento web.",
    "Transporte": "Desplazamientos: combustible, transporte público, taxi y VTC.",
    "Viajes": "Viajes: billetes de avión, hoteles y gastos durante el viaje (comida, transporte, ocio).",
    "Servicios básicos": "Suministros y comunicaciones: electricidad, gas y calefacción, internet.",
    "Nómina": "Sueldo y pagos regulares de la empresa.",
    "Ahorro": "Traspasos entre tu cuenta principal y otras cuentas de ahorro o inversión que no están en la app. "
    "No cuentan como gasto ni como ingreso.",
    "Otros": "Lo que no encaja en ninguna otra categoría.",
}
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
        CategoryEntry(
            name, DEFAULT_DESCRIPTIONS.get(name, ""), [SubEntry(sub) for sub in subs]
        )
        for name, subs in DEFAULT_TAXONOMY.items()
    ]
    income = [CategoryEntry(name, DEFAULT_DESCRIPTIONS.get(name, ""), kind=KIND_INCOME) for name in DEFAULT_INCOME_CATEGORIES]
    saving = [
        CategoryEntry(name, DEFAULT_DESCRIPTIONS.get(name, ""), [SubEntry(sub) for sub in subs], KIND_SAVING)
        for name, subs in DEFAULT_SAVING_CATEGORIES.items()
    ]
    return [*expenses[:-1], *income, *saving, expenses[-1]]  # Otros stays last


def category_names(taxonomy: Taxonomy, kind: str | None = None) -> list[str]:
    """Names in order; with `kind`, only that kind (Otros, available to all, is always included)."""
    return [c.name for c in taxonomy if kind is None or c.kind == kind or c.name == OTHERS]


def saving_names(taxonomy: Taxonomy) -> set[str]:
    return {c.name for c in taxonomy if c.kind == KIND_SAVING}


def kind_for_amount(amount: float) -> str:
    return KIND_INCOME if amount > 0 else KIND_EXPENSE


def for_amount(taxonomy: Taxonomy, amount: float) -> Taxonomy:
    """The categories a movement of this amount can have: its own kind, the saving ones and Otros."""
    kind = kind_for_amount(amount)
    return [c for c in taxonomy if c.kind in (kind, KIND_SAVING) or c.name == OTHERS]


def clean_kind(raw: str | None) -> str:
    if raw not in KINDS:
        raise ValueError("El tipo debe ser gasto, ingreso o ahorro")
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
