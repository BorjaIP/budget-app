import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

from .. import styles
from ..views.charts import StatsState


def budget_stat_card(
    stat_name: str,
    value_var: rx.Var[str],
    icon: str,
    icon_color: LiteralAccentColor,
) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(
                    rx.icon(tag=icon, size=34),
                    color_scheme=icon_color,
                    radius="full",
                    padding="0.7rem",
                ),
                rx.vstack(
                    rx.heading(
                        value_var,
                        size="6",
                        weight="bold",
                    ),
                    rx.text(stat_name, size="4", weight="medium"),
                    spacing="1",
                    height="100%",
                    align_items="start",
                    width="100%",
                ),
                height="100%",
                spacing="4",
                align="center",
                width="100%",
            ),
            spacing="3",
        ),
        size="3",
        width="100%",
        box_shadow=styles.box_shadow_style,
    )


def budget_stats_cards() -> rx.Component:
    return rx.grid(
        budget_stat_card(
            stat_name="Total Ingresos",
            value_var=StatsState.total_ingresos_fmt,
            icon="trending-up",
            icon_color="green",
        ),
        budget_stat_card(
            stat_name="Total Gastos",
            value_var=StatsState.total_gastos_fmt,
            icon="trending-down",
            icon_color="red",
        ),
        budget_stat_card(
            stat_name="Saldo Neto",
            value_var=StatsState.saldo_neto_fmt,
            icon="wallet",
            icon_color="teal",
        ),
        gap="1rem",
        grid_template_columns=[
            "1fr",
            "repeat(1, 1fr)",
            "repeat(2, 1fr)",
            "repeat(3, 1fr)",
            "repeat(3, 1fr)",
        ],
        width="100%",
    )
