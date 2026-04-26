import reflex as rx

from ..components.card import card
from ..templates import template
from ..views.charts import (
    StatsState,
    date_filter_controls,
    ingresos_gastos_chart,
    saldo_chart,
)
from ..views.stats_cards import budget_stats_cards


@template(route="/", title="Resumen", on_load=StatsState.load_chart_data)  # type: ignore
def index() -> rx.Component:
    """The overview page."""
    return rx.vstack(
        rx.heading("Resumen", size="5"),
        budget_stats_cards(),
        date_filter_controls(),
        rx.grid(
            card(
                rx.hstack(
                    rx.icon("bar-chart-3", size=20, color=rx.color("teal", 9)),
                    rx.text("Ingresos vs Gastos", size="4", weight="medium"),
                    align="center",
                    spacing="2",
                    margin_bottom="0.5em",
                ),
                ingresos_gastos_chart(),
            ),
            card(
                rx.hstack(
                    rx.icon("wallet", size=20),
                    rx.text("Saldo", size="4", weight="medium"),
                    align="center",
                    spacing="2",
                    margin_bottom="0.5em",
                ),
                saldo_chart(),
            ),
            gap="1rem",
            grid_template_columns=[
                "1fr",
                "1fr",
                "1fr",
                "repeat(2, 1fr)",
                "repeat(2, 1fr)",
            ],
            width="100%",
        ),
        spacing="6",
        width="100%",
    )
