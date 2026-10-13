import reflex as rx

from ..views.charts import StatsState


def _stat(label: str, value_var, color=None, delta_var=None, lead=False, **props) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", color=rx.color("gray", 11)),
        rx.skeleton(
            rx.heading(
                value_var,
                as_="p",
                color=color if color is not None else rx.color("gray", 12),
                size=rx.breakpoints(initial="6", sm="7", lg="8") if lead else rx.breakpoints(initial="4", sm="5", lg="6"),
                weight="medium",
                letter_spacing="-0.02em",
                class_name="num",
            ),
            loading=StatsState.is_loading,
            min_width="6em",
        ),
        rx.cond(
            delta_var != "",
            rx.text(delta_var, size="1", color=rx.color("gray", 11), class_name="num"),
        )
        if delta_var is not None
        else rx.fragment(),
        spacing="1",
        align="start",
        width="100%",
        padding=["1rem", "1rem", "1.25rem", "1.5rem", "1.5rem"],
        background="var(--color-panel-solid)",
        **props,
    )


def budget_stats_cards() -> rx.Component:
    """One bordered strip; the balance leads and the 1px gaps show the container color as dividers."""
    return rx.grid(
        _stat(
            "Saldo",
            StatsState.net_balance_fmt,
            lead=True,
            grid_column=["span 2", "span 2", "span 2", "span 1", "span 1"],
        ),
        _stat("Ingresos", StatsState.total_income_fmt, rx.color("green", 11), StatsState.income_delta),
        _stat("Gastos", StatsState.total_spending_fmt, rx.color("red", 11), StatsState.spending_delta),
        _stat("Tasa de ahorro", StatsState.savings_rate_fmt),
        gap="1px",
        grid_template_columns=[
            "repeat(2, 1fr)",
            "repeat(2, 1fr)",
            "repeat(2, 1fr)",
            "1.5fr 1fr 1fr 1fr",
            "1.5fr 1fr 1fr 1fr",
        ],
        width="100%",
        overflow="hidden",
        border=f"1px solid {rx.color('gray', 5, True)}",
        border_radius="var(--radius-4)",
        background=rx.color("gray", 5, True),
    )
