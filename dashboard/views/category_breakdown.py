"""Spending by category as a ranked list with proportional bars (no legend needed)."""

import reflex as rx

from dashboard.views.charts import StatsState

_TRUNCATE = {"overflow": "hidden", "text_overflow": "ellipsis", "white_space": "nowrap"}


def _row(item) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(item["name"], size="2", flex="1", min_width="0", style=_TRUNCATE),
            rx.text(
                item["value_fmt"],
                size="2",
                weight="medium",
                class_name="num",
                flex_shrink="0",
                style={"white_space": "nowrap"},
            ),
            rx.text(
                item["percent_fmt"],
                size="1",
                color=rx.color("gray", 11),
                class_name="num",
                flex_shrink="0",
                width="4.5em",
                text_align="right",
            ),
            align="center",
            spacing="3",
            width="100%",
        ),
        rx.box(
            rx.box(
                width=item["bar"],
                height="100%",
                background=rx.color("gray", 12),
                border_radius="2px",
            ),
            width="100%",
            height="3px",
            background=rx.color("gray", 4, True),
            border_radius="2px",
        ),
        spacing="2",
        width="100%",
        padding_y="0.5em",
    )


def category_breakdown() -> rx.Component:
    return rx.cond(
        StatsState.category_breakdown.length() == 0,
        rx.center(
            rx.text("Sin gastos categorizados todavía", size="2", color=rx.color("gray", 11)),
            height="200px",
        ),
        rx.vstack(
            rx.foreach(StatsState.category_breakdown, _row),
            spacing="0",
            width="100%",
        ),
    )
