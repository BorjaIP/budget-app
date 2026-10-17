"""The learned merchant rules, listed so the user can see, change, add and forget them."""

import logging

import pydantic
import reflex as rx

from dashboard.database.operations import db_manager
from dashboard.taxonomy import NO_SUBCATEGORY
from dashboard.taxonomy_state import category_color

logger = logging.getLogger(__name__)

MAX_VISIBLE = 150


class RuleRow(pydantic.BaseModel):
    key: str = ""
    example: str = ""
    category: str = ""
    subcategory: str = ""
    color: str = "gray"
    confirmations: int = 1
    confirmations_text: str = ""


class RulesState(rx.State):
    rules: list[RuleRow] = []
    search: str = ""
    options: dict[str, list[str]] = {}  # category -> its subcategories

    new_text: str = ""
    new_category: str = ""
    new_subcategory: str = NO_SUBCATEGORY

    show_edit: bool = False
    edit_key: str = ""
    edit_example: str = ""
    edit_category: str = ""
    edit_subcategory: str = NO_SUBCATEGORY

    show_delete: bool = False
    delete_key: str = ""
    delete_example: str = ""

    @rx.var(cache=True)
    def category_options(self) -> list[str]:
        return list(self.options)

    @rx.var(cache=True)
    def new_sub_options(self) -> list[str]:
        return [NO_SUBCATEGORY, *self.options.get(self.new_category, [])]

    @rx.var(cache=True)
    def edit_sub_options(self) -> list[str]:
        return [NO_SUBCATEGORY, *self.options.get(self.edit_category, [])]

    @rx.var(cache=True)
    def visible_rules(self) -> list[RuleRow]:
        needle = self.search.strip().lower()
        rows = [
            r for r in self.rules
            if not needle or needle in r.example.lower() or needle in r.category.lower() or needle in r.subcategory.lower()
        ]
        return rows[:MAX_VISIBLE]

    @rx.var(cache=True)
    def rules_summary(self) -> str:
        total = len(self.rules)
        if total == 0:
            return "Todavía no hay reglas. Se crean solas cada vez que corriges una categoría a mano."
        noun = "regla" if total == 1 else "reglas"
        return f"{total} {noun}. Se aplican a los movimientos del mismo comercio o muy parecidos."

    # ------------------------------------------------------------------ load
    @rx.event
    def load_rules(self):
        try:
            db_manager.sync_merchant_memory()  # corrections made before rules existed show up too
            taxonomy = db_manager.taxonomy.load()
            self.options = {c.name: [s.name for s in c.subcategories] for c in taxonomy}
            self.rules = [
                RuleRow(
                    key=r["key"],
                    example=r["example"],
                    category=r["category"],
                    subcategory=r["subcategory"] or "",
                    color=category_color(r["category"]),
                    confirmations=r["confirmations"],
                    confirmations_text=(
                        "Confirmada " + str(r["confirmations"]) + " veces" if r["confirmations"] > 1 else "Confirmada 1 vez"
                    ),
                )
                for r in db_manager.list_rules()
            ]
            if not self.new_category and self.options:
                self.new_category = next(iter(self.options))
        except Exception:
            logger.exception("Could not load the rules")
            return rx.toast.error("No se pudieron cargar las reglas")

    @rx.event
    def set_search(self, value: str):
        self.search = value

    # ---------------------------------------------------------------- create
    @rx.event
    def set_new_text(self, value: str):
        self.new_text = value

    @rx.event
    def set_new_category(self, value: str):
        self.new_category = value
        self.new_subcategory = NO_SUBCATEGORY

    @rx.event
    def set_new_subcategory(self, value: str):
        self.new_subcategory = value

    def create_rule(self):
        return self._save(self.new_text, self.new_category, self.new_subcategory, reset_form=True)

    # ------------------------------------------------------------------ edit
    def open_edit(self, key: str):
        rule = next((r for r in self.rules if r.key == key), None)
        if rule is None:
            return
        self.edit_key, self.edit_example = key, rule.example
        self.edit_category = rule.category
        self.edit_subcategory = rule.subcategory or NO_SUBCATEGORY
        self.show_edit = True

    @rx.event
    def set_edit_category(self, value: str):
        self.edit_category = value
        self.edit_subcategory = NO_SUBCATEGORY

    @rx.event
    def set_edit_subcategory(self, value: str):
        self.edit_subcategory = value

    @rx.event
    def set_show_edit(self, value: bool):
        self.show_edit = value

    def save_edit(self):
        self.show_edit = False
        return self._save(self.edit_example, self.edit_category, self.edit_subcategory)

    def _save(self, text: str, category: str, subcategory: str, reset_form: bool = False):
        try:
            _, changed = db_manager.save_rule(text, category, None if subcategory == NO_SUBCATEGORY else subcategory)
        except ValueError as error:
            return rx.toast.error(str(error))
        except Exception:
            logger.exception("Could not save the rule")
            return rx.toast.error("No se pudo guardar la regla")
        if reset_form:
            self.new_text = ""
            self.new_subcategory = NO_SUBCATEGORY
        self.load_rules()
        note = f" y aplicada a {changed} movimientos" if changed else ""
        return rx.toast.success("Regla guardada" + note)

    # ---------------------------------------------------------------- delete
    def open_delete(self, key: str):
        rule = next((r for r in self.rules if r.key == key), None)
        self.delete_key, self.delete_example = key, rule.example if rule else key
        self.show_delete = True

    @rx.event
    def set_show_delete(self, value: bool):
        self.show_delete = value

    def confirm_delete(self):
        self.show_delete = False
        try:
            reopened = db_manager.delete_rule(self.delete_key)
        except Exception:
            logger.exception("Could not delete the rule")
            return rx.toast.error("No se pudo borrar la regla")
        self.load_rules()
        note = f" ({reopened} movimientos vuelven a revisión)" if reopened else ""
        return rx.toast.success("Regla borrada" + note)
