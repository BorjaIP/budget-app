import reflex as rx

from ..components.card import card

from ..views.charts import StatsState


def _spark(data, color) -> rx.Component:
    """A tiny trend line with no axes: the shape of the last months at a glance."""
    return rx.recharts.area_chart(
        rx.recharts.area(
            data_key="v", stroke=color, fill=color, fill_opacity=0.12, stroke_width=1.5, dot=False,
            is_animation_active=False,
        ),
        rx.recharts.y_axis(hide=True, domain=["dataMin", "dataMax"]),
        data=data,
        height=44,
        width="100%",
        margin={"top": 4, "right": 0, "bottom": 0, "left": 0},
    )


def _stat(label: str, value_var, color=None, delta_var=None, lead=False, spark=None, spark_color=None, **props) -> rx.Component:
    return card(
        rx.text(label, size="2", color=rx.color("gray", 11)),
        rx.skeleton(
            rx.heading(
                value_var,
                as_="p",
                color=color if color is not None else rx.color("gray", 12),
                size=rx.breakpoints(initial="6", sm="7", lg="8") if lead else rx.breakpoints(initial="5", sm="6", lg="7"),
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
        rx.cond(spark.length() > 1, rx.box(_spark(spark, spark_color), margin_top="0.5rem")) if spark is not None else rx.fragment(),
        display="flex",
        flex_direction="column",
        gap="0.375rem",
        **props,
    )


def budget_stats_cards() -> rx.Component:
    """Four separate cards; the balance leads."""
    return rx.grid(
        _stat(
            "Saldo",
            StatsState.net_balance_fmt,
            lead=True,
            spark=StatsState.spark_balance,
            spark_color=rx.color("gray", 11),
            grid_column=["span 2", "span 2", "span 2", "span 1", "span 1"],
        ),
        _stat(
            "Ingresos", StatsState.total_income_fmt, rx.color("green", 11), StatsState.income_delta,
            spark=StatsState.spark_income, spark_color=rx.color("green", 9),
        ),
        _stat(
            "Gastos", StatsState.total_spending_fmt, rx.color("red", 11), StatsState.spending_delta,
            spark=StatsState.spark_spending, spark_color=rx.color("red", 9),
        ),
        _stat(
            "Tasa de ahorro", StatsState.savings_rate_fmt, delta_var=StatsState.saved_note,
            spark=StatsState.spark_rate, spark_color=rx.color("gray", 11),
        ),
        gap="1rem",
        grid_template_columns=[
            "repeat(2, 1fr)",
            "repeat(2, 1fr)",
            "repeat(2, 1fr)",
            "1.5fr 1fr 1fr 1fr",
            "1.5fr 1fr 1fr 1fr",
        ],
        width="100%",
    )
