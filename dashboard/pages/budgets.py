"""Monthly budget per category against the spending of the latest month in the data."""

import logging

import reflex as rx

from ..budgets import BudgetRow, _money, build_rows, parse_limit
from ..components.card import card
from ..components.empty_state import empty_state
from ..components.notice import error_notice
from ..components.page_header import page_header
from ..database.operations import db_manager
from ..taxonomy import category_names
from ..periods import resolve_period
from ..recurring import RecurringRow, find_recurring
from ..templates import template
from ..views.charts import _humanize_month

logger = logging.getLogger(__name__)


class BudgetState(rx.State):
    rows: list[BudgetRow] = []
    recurring: list[RecurringRow] = []
    recurring_total_fmt: str = ""
    month_label: str = ""
    has_data: bool = False
    load_error: bool = False

    @rx.event
    def load_budgets(self):
        self.load_error = False
        try:
            _, latest = db_manager.get_date_bounds()
            self.has_data = latest is not None
            if latest is None:
                self.rows = []
                self.month_label = ""
                return
            period = resolve_period("month", latest)
            self.month_label = _humanize_month(latest[:7])
            spending = {
                row["name"]: row["value"]
                for row in db_manager.get_category_breakdown(period.date_from, period.date_to)
            }
            self.recurring = find_recurring(db_manager.get_all_expenses())
            self.recurring_total_fmt = _money(sum(r.amount for r in self.recurring))
            self.rows = build_rows(category_names(db_manager.taxonomy.load()), db_manager.get_budgets(), spending)
        except Exception:
            logger.exception("Could not load the budgets")
            self.load_error = True

    @rx.event
    def save_limit(self, category: str, text: str):
        try:
            db_manager.set_budget(category, parse_limit(text))
        except Exception:
            logger.exception("Could not save the budget")
            return rx.toast.error("No se pudo guardar el presupuesto")
        return BudgetState.load_budgets


def _progress(row: BudgetRow) -> rx.Component:
    return rx.cond(
        row.has_limit,
        rx.vstack(
            rx.box(
                rx.box(
                    width=row.bar,
                    height="100%",
                    background=rx.cond(row.over, rx.color("red", 9), rx.color("gray", 12)),
                    border_radius="2px",
                ),
                width="100%",
                height="4px",
                background=rx.color("gray", 4, True),
                border_radius="2px",
            ),
            rx.hstack(
                rx.text(
                    row.spent_fmt + " de " + row.limit_fmt,
                    size="1",
                    color=rx.color("gray", 11),
                    class_name="num",
                ),
                rx.text(
                    row.remaining_fmt,
                    size="1",
                    class_name="num",
                    color=rx.cond(row.over, rx.color("red", 11), rx.color("gray", 11)),
                ),
                justify="between",
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),
        rx.text(
            row.spent_fmt + " este mes · sin límite",
            size="1",
            color=rx.color("gray", 11),
            class_name="num",
        ),
    )


def _row(row: BudgetRow) -> rx.Component:
    return rx.flex(
        rx.vstack(
            rx.text(row.category, size="2", weight="medium"),
            _progress(row),
            spacing="2",
            flex="1",
            min_width="0",
        ),
        rx.input(
            default_value=row.limit_text,
            key=row.category + row.limit_text,
            placeholder="Límite al mes",
            on_blur=lambda text: BudgetState.save_limit(row.category, text),
            size="2",
            width=["100%", "9rem"],
            custom_attrs={"aria-label": "Límite mensual de " + row.category, "inputMode": "decimal"},
        ),
        direction=rx.breakpoints(initial="column", sm="row"),
        align=rx.breakpoints(initial="stretch", sm="center"),
        gap="0.75rem",
        padding_y="0.75rem",
        border_bottom=f"1px solid {rx.color('gray', 4, True)}",
        width="100%",
    )


def _recurring_row(row: RecurringRow) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(row.concept),
        rx.table.cell(rx.text(row.months, class_name="num"), justify="end"),
        rx.table.cell(rx.text(row.last_date_fmt, class_name="num"), justify="end"),
        rx.table.cell(rx.text(row.amount_fmt, weight="medium", class_name="num"), justify="end"),
    )


def _recurring_card() -> rx.Component:
    return rx.cond(
        BudgetState.recurring.length() > 0,
        card(
            rx.text(
                "Unos " + BudgetState.recurring_total_fmt + " al mes en cargos que se repiten.",
                size="2",
                color=rx.color("gray", 11),
                margin_bottom="0.75rem",
            ),
            rx.scroll_area(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Concepto"),
                            rx.table.column_header_cell("Meses", justify="end"),
                            rx.table.column_header_cell("Último cargo", justify="end"),
                            rx.table.column_header_cell("Importe", justify="end"),
                        )
                    ),
                    rx.table.body(rx.foreach(BudgetState.recurring, _recurring_row)),
                    variant="ghost",
                    width="100%",
                    min_width="28rem",
                ),
                type="auto",
                scrollbars="horizontal",
                width="100%",
            ),
            title="Cargos recurrentes",
        ),
    )


@template(route="/budgets", title="Presupuestos", on_load=BudgetState.load_budgets)
def budgets() -> rx.Component:
    return rx.vstack(
        page_header(
            "Presupuestos",
            rx.cond(
                BudgetState.has_data,
                "Gasto de " + BudgetState.month_label + " frente a tu límite mensual por categoría.",
                "Fija un límite mensual por categoría.",
            ),
        ),
        rx.cond(
            BudgetState.load_error,
            error_notice("No se pudieron cargar los presupuestos.", BudgetState.load_budgets),
        ),
        rx.cond(
            BudgetState.has_data,
            card(rx.vstack(rx.foreach(BudgetState.rows, _row), spacing="0", width="100%")),
            empty_state(
                "cloud-upload",
                "Aún no hay datos",
                "Sube un extracto bancario en la sección Gastos para fijar presupuestos.",
            ),
        ),
        _recurring_card(),
        spacing="6",
        width="100%",
    )
