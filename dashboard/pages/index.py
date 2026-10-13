import reflex as rx

from ..components.card import card
from ..components.empty_state import empty_state
from ..components.icon import icon
from ..components.notice import error_notice
from ..components.page_header import page_header
from ..templates import template
from .. import styles
from ..views.overview_cards import (
    cashflow_card,
    categories_card,
    insights_card,
    movers_card,
    pace_card,
    upcoming_card,
)
from ..views.charts import (
    StatsState,
    date_filter_controls,
    income_spending_chart,
    balance_chart,
)
from ..views.recent_transactions import recent_transactions
from ..views.stats_cards import budget_stats_cards
from ..views.top_concepts import top_concepts
from ..views.unusual_charges import unusual_charges


@template(route="/", title="Resumen", on_load=StatsState.load_chart_data)
def index() -> rx.Component:
    has_data = StatsState.chart_data.length() > 0
    return rx.vstack(
        page_header("Resumen", actions=date_filter_controls()),
        rx.cond(
            StatsState.load_error,
            error_notice("No se pudieron cargar los datos.", StatsState.load_chart_data),
        ),
        rx.cond(
            StatsState.review_count > 0,
            rx.flex(
                rx.hstack(
                    icon("info-circled", size=16),
                    rx.text(StatsState.review_label, size="2"),
                    spacing="2",
                    align="center",
                ),
                rx.button("Revisar", variant="soft", color_scheme="gray", size="2", on_click=StatsState.review_pending),
                justify="between",
                align="center",
                gap="1rem",
                width="100%",
                padding="0.75rem 1rem",
                border=styles.border,
                border_radius=styles.card_radius,
                background="var(--color-panel-solid)",
                box_shadow=styles.card_shadow,
            ),
        ),
        budget_stats_cards(),
        rx.cond(
            has_data | StatsState.is_loading | StatsState.load_error,
            rx.vstack(
                insights_card(),
                rx.grid(
                    cashflow_card(),
                    categories_card(),
                    gap="1rem",
                    grid_template_columns=["1fr", "1fr", "1fr", "3fr 2fr", "3fr 2fr"],
                    align_items="stretch",
                    width="100%",
                ),
                rx.grid(
                    pace_card(),
                    movers_card(),
                    upcoming_card(),
                    gap="1rem",
                    grid_template_columns="repeat(auto-fit, minmax(20rem, 1fr))",
                    align_items="stretch",
                    width="100%",
                ),
                rx.grid(
                    card(income_spending_chart(), title="Ingresos vs gastos"),
                    card(balance_chart(), title="Evolución del saldo"),
                    gap="1rem",
                    grid_template_columns=["1fr", "1fr", "1fr", "3fr 2fr", "3fr 2fr"],
                    align_items="stretch",
                    width="100%",
                ),
                rx.grid(
                    card(top_concepts(), title="Top conceptos"),
                    card(recent_transactions(), title="Movimientos recientes"),
                    unusual_charges(),
                    gap="1rem",
                    grid_template_columns="repeat(auto-fit, minmax(20rem, 1fr))",
                    align_items="stretch",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            empty_state(
                "cloud-upload",
                "Aún no hay datos",
                "Sube un extracto bancario en la sección Transacciones para ver tu resumen aquí.",
            ),
        ),
        spacing="5",
        width="100%",
    )
