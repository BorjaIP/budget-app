import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

from .. import styles
from ..views.charts import StatsState


def budget_stat_card(
    stat_name: str,
    value_var,
    icon: str,
    icon_color: LiteralAccentColor | rx.Var,
) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.badge(
                rx.icon(tag=icon, size=28),
                color_scheme=icon_color,
                radius="full",
                padding="0.7rem",
            ),
            rx.vstack(
                rx.heading(value_var, size="6", weight="bold"),
                rx.text(stat_name, size="3", weight="medium", color=rx.color("gray", 11)),
                spacing="1",
                align_items="start",
                width="100%",
            ),
            spacing="4",
            align="center",
            width="100%",
        ),
        size="3",
        width="100%",
        box_shadow=styles.box_shadow_style,
    )


def budget_stats_cards() -> rx.Component:
    return rx.grid(
        budget_stat_card(
            "Ingresos",
            StatsState.total_ingresos_fmt,
            "trending-up",
            "green",
        ),
        budget_stat_card(
            "Gastos",
            StatsState.total_gastos_fmt,
            "trending-down",
            "red",
        ),
        budget_stat_card(
            "Saldo",
            StatsState.saldo_neto_fmt,
            "wallet",
            "teal",
        ),
        budget_stat_card(
            "Tasa de ahorro",
            StatsState.savings_rate_fmt,
            "piggy-bank",
            StatsState.savings_rate_color,
        ),
        gap="1rem",
        grid_template_columns=[
            "1fr",
            "repeat(2, 1fr)",
            "repeat(2, 1fr)",
            "repeat(4, 1fr)",
            "repeat(4, 1fr)",
        ],
        width="100%",
    )
