"""Reactive view of the user's taxonomy and the events that edit it."""

import logging

import pydantic
import reflex as rx

from dashboard.database.operations import db_manager
from dashboard.database.taxonomy_repository import TaxonomyError
from dashboard.taxonomy import FALLBACK, KIND_EXPENSE, KIND_INCOME, NO_SUBCATEGORY, OTHERS

logger = logging.getLogger(__name__)

# The owner's original categories keep the colors they always had; new ones get a stable color from their name.
DEFAULT_COLORS = {
    "Deuda": "ruby",
    "Educación": "indigo",
    "Ocio": "purple",
    "Gastos diarios": "amber",
    "Regalos": "pink",
    "Salud/médicos": "tomato",
    "Vivienda": "blue",
    "Tecnología": "iris",
    "Transporte": "cyan",
    "Viajes": "teal",
    "Servicios básicos": "green",
    "Nómina": "jade",
    "Otros": "gray",
}
_PALETTE = ["crimson", "orange", "lime", "plum", "sky", "mint", "bronze", "violet", "jade", "brown", "yellow", "grass"]


def category_color(name: str) -> str:
    if name in DEFAULT_COLORS:
        return DEFAULT_COLORS[name]
    return _PALETTE[sum(ord(ch) for ch in name) % len(_PALETTE)]


class SubRow(pydantic.BaseModel):
    name: str = ""
    description: str = ""
    reserved: bool = False


KIND_LABELS = {KIND_EXPENSE: "Gasto", KIND_INCOME: "Ingreso"}
KIND_BY_LABEL = {label: kind for kind, label in KIND_LABELS.items()}


class CategoryRow(pydantic.BaseModel):
    name: str = ""
    kind: str = KIND_EXPENSE
    description: str = ""
    color: str = "gray"
    reserved: bool = False
    subcategories: list[SubRow] = []


class TaxonomyState(rx.State):
    rows: list[CategoryRow] = []
    colors: dict[str, str] = {}

    # category picker of a movement (one popover is open at a time)
    picker_category: str = ""
    picker_subcategory: str = NO_SUBCATEGORY
    picker_kind: str = KIND_EXPENSE  # kind of the movement being categorized

    # edit dialog
    show_edit: bool = False
    edit_kind: str = ""  # category | subcategory
    edit_category: str = ""
    edit_original: str = ""
    edit_name: str = ""
    edit_description: str = ""
    edit_type_label: str = KIND_LABELS[KIND_EXPENSE]

    # delete dialog
    show_delete: bool = False
    delete_kind: str = ""
    delete_category: str = ""
    delete_name: str = ""
    delete_message: str = ""

    show_reset: bool = False

    @rx.var(cache=True)
    def categories(self) -> list[str]:
        return [row.name for row in self.rows]

    @rx.var(cache=True)
    def expense_rows(self) -> list[CategoryRow]:
        return [r for r in self.rows if r.kind == KIND_EXPENSE]

    @rx.var(cache=True)
    def income_rows(self) -> list[CategoryRow]:
        return [r for r in self.rows if r.kind == KIND_INCOME]

    @rx.var(cache=True)
    def picker_categories(self) -> list[str]:
        """Categories a movement can be moved to: those of its kind, plus Otros."""
        return [r.name for r in self.rows if r.kind == self.picker_kind or r.reserved]

    @rx.var(cache=True)
    def categories_and_unassigned(self) -> list[str]:
        return [*self.categories, "Sin categorizar"]

    @rx.var(cache=True)
    def picker_subcategories(self) -> list[str]:
        row = next((r for r in self.rows if r.name == self.picker_category), None)
        return [NO_SUBCATEGORY, *(s.name for s in row.subcategories)] if row else [NO_SUBCATEGORY]

    # ------------------------------------------------------------------ load
    @rx.event
    def load_taxonomy(self):
        try:
            taxonomy = db_manager.taxonomy.load()
        except Exception:
            logger.exception("Could not load the categories")
            return rx.toast.error("No se pudieron cargar las categorías")
        self.rows = [
            CategoryRow(
                name=c.name,
                description=c.description,
                kind=c.kind,
                color=category_color(c.name),
                reserved=c.name == OTHERS,
                subcategories=[
                    SubRow(name=s.name, description=s.description, reserved=(c.name, s.name) == FALLBACK)
                    for s in c.subcategories
                ],
            )
            for c in taxonomy
        ]
        self.colors = {row.name: row.color for row in self.rows}

    def _apply(self, action, success: str):
        """Run a repository change; show its message when the taxonomy refuses it."""
        try:
            affected = action()
        except (TaxonomyError, ValueError) as error:
            return rx.toast.error(str(error))
        except Exception:
            logger.exception("Could not change the categories")
            return rx.toast.error("No se pudo guardar el cambio")
        self.load_taxonomy()
        note = f" ({affected} movimientos actualizados)" if affected else ""
        return rx.toast.success(success + note)

    # ------------------------------------------------------------- add forms
    def add_category(self, form: dict):
        return self._apply(
            lambda: db_manager.taxonomy.add_category(
                form.get("name", ""),
                form.get("description", ""),
                KIND_BY_LABEL.get(form.get("kind", ""), KIND_EXPENSE),
            ),
            "Categoría añadida",
        )

    def add_subcategory(self, form: dict):
        return self._apply(
            lambda: db_manager.taxonomy.add_subcategory(
                form.get("category", ""), form.get("name", ""), form.get("description", "")
            ),
            "Subcategoría añadida",
        )

    # ----------------------------------------------------------------- edit
    def open_edit_category(self, name: str):
        row = next((r for r in self.rows if r.name == name), None)
        self.edit_kind, self.edit_category, self.edit_original = "category", name, name
        self.edit_name, self.edit_description = name, row.description if row else ""
        self.edit_type_label = KIND_LABELS.get(row.kind if row else KIND_EXPENSE, KIND_LABELS[KIND_EXPENSE])
        self.show_edit = True

    def open_edit_subcategory(self, category: str, name: str):
        row = next((r for r in self.rows if r.name == category), None)
        sub = next((s for s in row.subcategories if s.name == name), None) if row else None
        self.edit_kind, self.edit_category, self.edit_original = "subcategory", category, name
        self.edit_name, self.edit_description = name, sub.description if sub else ""
        self.show_edit = True

    @rx.event
    def set_edit_name(self, value: str):
        self.edit_name = value

    @rx.event
    def set_edit_description(self, value: str):
        self.edit_description = value

    @rx.event
    def set_edit_type_label(self, value: str):
        self.edit_type_label = value

    @rx.event
    def set_show_edit(self, value: bool):
        self.show_edit = value

    def save_edit(self):
        kind, category, original = self.edit_kind, self.edit_category, self.edit_original
        name, description = self.edit_name, self.edit_description
        if kind == "category":
            result = self._apply(
                lambda: db_manager.taxonomy.update_category(
                    original,
                    new_name=name,
                    description=description,
                    kind=None if original == OTHERS else KIND_BY_LABEL.get(self.edit_type_label),
                ),
                "Categoría actualizada",
            )
        else:
            result = self._apply(
                lambda: db_manager.taxonomy.update_subcategory(category, original, new_name=name, description=description),
                "Subcategoría actualizada",
            )
        self.show_edit = False
        return result

    # --------------------------------------------------------------- delete
    def open_delete_category(self, name: str):
        count = db_manager.count_expenses_in(name)
        self.delete_kind, self.delete_category, self.delete_name = "category", name, name
        self.delete_message = (
            f"Se borrará la categoría «{name}» con todas sus subcategorías. "
            f"{count} movimientos pasarán a Otros / General y se olvidarán sus comercios aprendidos y su presupuesto."
        )
        self.show_delete = True

    def open_delete_subcategory(self, category: str, name: str):
        count = db_manager.count_expenses_in(category, name)
        self.delete_kind, self.delete_category, self.delete_name = "subcategory", category, name
        self.delete_message = (
            f"Se borrará la subcategoría «{name}». "
            f"{count} movimientos se quedarán solo en «{category}»."
        )
        self.show_delete = True

    @rx.event
    def set_show_delete(self, value: bool):
        self.show_delete = value

    def confirm_delete(self):
        kind, category, name = self.delete_kind, self.delete_category, self.delete_name
        self.show_delete = False
        if kind == "category":
            return self._apply(lambda: db_manager.taxonomy.delete_category(name), "Categoría borrada")
        return self._apply(lambda: db_manager.taxonomy.delete_subcategory(category, name), "Subcategoría borrada")

    # ---------------------------------------------------------------- reset
    @rx.event
    def set_show_reset(self, value: bool):
        self.show_reset = value

    def confirm_reset(self):
        self.show_reset = False
        return self._apply(db_manager.taxonomy.reset_to_defaults, "Categorías originales restauradas")

    # --------------------------------------------------------------- picker
    def open_picker(self, category: str | None, subcategory: str | None, is_expense: bool = True):
        self.picker_kind = KIND_EXPENSE if is_expense else KIND_INCOME
        self.picker_category = category or ""
        self.picker_subcategory = subcategory or NO_SUBCATEGORY

    @rx.event
    def set_picker_category(self, value: str):
        self.picker_category = value
        self.picker_subcategory = NO_SUBCATEGORY

    @rx.event
    def set_picker_subcategory(self, value: str):
        self.picker_subcategory = value
