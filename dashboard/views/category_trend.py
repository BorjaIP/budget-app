"""Monthly spending of one category over the last twelve months."""

import logging

import reflex as rx

from dashboard.database.operations import db_manager
from dashboard.llm.llm_call import CATEGORY_TAXONOMY
from dashboard.trends import ALL, UNCATEGORIZED, monthly_category_totals
from dashboard.views.charts import _CHART_HEIGHT, _Y_TICK_FORMATTER, _custom_tooltip, _x_axis

logger = logging.getLogger(__name__)

CATEGORY_OPTIONS = [ALL, *CATEGORY_TAXONOMY, UNCATEGORIZED]


class CategoryTrendState(rx.State):
    category: str = ALL
    data: list[dict] = []
    load_error: bool = False

    @rx.event
    def load_trend(self):
        self.load_error = False
        try:
            _, latest = db_manager.get_date_bounds()
            self.data = monthly_category_totals(db_manager.get_all_expenses(), self.category, latest)
        except Exception:
            logger.exception("Could not load the category trend")
            self.load_error = True
            self.data = []

    @rx.event
    def set_category(self, value: str):
        self.category = value
        return CategoryTrendState.load_trend


def category_trend() -> rx.Component:
    return rx.vstack(
        rx.select(
            CATEGORY_OPTIONS,
            value=CategoryTrendState.category,
            on_change=CategoryTrendState.set_category,
            size="2",
            custom_attrs={"aria-label": "Categoría"},
        ),
        rx.cond(
            CategoryTrendState.data.length() == 0,
            rx.center(
                rx.text("No hay datos para mostrar", size="2", color=rx.color("gray", 11)),
                height="200px",
                width="100%",
            ),
            rx.recharts.bar_chart(
                _custom_tooltip(),
                rx.recharts.cartesian_grid(horizontal=True, vertical=False),
                rx.recharts.bar(name="Gasto", data_key="total", fill=rx.color("red", 9)),
                _x_axis("month"),
                rx.recharts.y_axis(
                    tick_formatter=_Y_TICK_FORMATTER, width=64, tick_line=False, axis_line=False
                ),
                data=CategoryTrendState.data,
                height=_CHART_HEIGHT,
            ),
        ),
        spacing="3",
        align="start",
        width="100%",
    )
