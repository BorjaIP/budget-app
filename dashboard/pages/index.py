import reflex as rx

from .. import styles
from ..components.empty_state import empty_state
from ..templates import template
from ..views.category_pie import category_pie
from ..views.charts import (
    StatsState,
    date_filter_controls,
    ingresos_gastos_chart,
    saldo_chart,
)
from ..views.recent_transactions import recent_transactions
from ..views.stats_cards import budget_stats_cards
from ..views.top_concepts import top_concepts


def _card(*children, title: str | None = None, icon: str | None = None) -> rx.Component:
    header = rx.fragment()
    if title:
        header = rx.hstack(
            rx.icon(icon or "circle-dot", size=18, color=rx.color("teal", 9)),
            rx.text(title, size="3", weight="medium"),
            align="center",
            spacing="2",
            margin_bottom="0.75em",
        )
    return rx.card(
        header,
        *children,
        size="3",
        width="100%",
        box_shadow=styles.box_shadow_style,
    )


@template(route="/", title="Resumen", on_load=StatsState.load_chart_data)
def index() -> rx.Component:
    has_data = StatsState.chart_data.length() > 0
    return rx.vstack(
        rx.hstack(
            rx.heading("Resumen", size="6"),
            rx.spacer(),
            date_filter_controls(),
            align="center",
            wrap="wrap",
            width="100%",
        ),
        budget_stats_cards(),
        rx.cond(
            has_data,
            rx.vstack(
                rx.grid(
                    _card(ingresos_gastos_chart(), title="Ingresos vs gastos", icon="bar-chart-3"),
                    _card(saldo_chart(), title="Evolución del saldo", icon="line-chart"),
                    gap="1rem",
                    grid_template_columns=["1fr", "1fr", "1fr", "repeat(2, 1fr)", "repeat(2, 1fr)"],
                    width="100%",
                ),
                rx.grid(
                    _card(category_pie(), title="Gasto por categoría", icon="pie-chart"),
                    _card(top_concepts(), title="Top conceptos", icon="trending-up"),
                    _card(recent_transactions(), title="Movimientos recientes", icon="receipt"),
                    gap="1rem",
                    grid_template_columns=["1fr", "1fr", "1fr", "repeat(3, 1fr)", "repeat(3, 1fr)"],
                    width="100%",
                ),
                spacing="6",
                width="100%",
            ),
            empty_state(
                "cloud-upload",
                "Aún no hay datos",
                "Sube un extracto bancario en la sección Gastos para ver tu resumen aquí.",
            ),
        ),
        spacing="6",
        width="100%",
    )
