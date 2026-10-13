"""Charges of the last weeks that stand out (very high for their category, or duplicated)."""

import reflex as rx

from dashboard.anomalies import UnusualRow
from dashboard.components.card import card
from dashboard.views.charts import StatsState


def _row(row: UnusualRow) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(row.concept, size="2", weight="medium"),
            rx.text(row.date_fmt + " · " + row.reason, size="1", color=rx.color("gray", 11)),
            spacing="1",
            align="start",
            flex="1",
            min_width="0",
        ),
        rx.text(
            "-" + row.amount_fmt,
            size="2",
            weight="medium",
            class_name="num",
            color=rx.color("red", 11),
            style={"white_space": "nowrap"},
        ),
        align="center",
        spacing="3",
        width="100%",
        padding_y="0.6em",
        border_bottom=f"1px solid {rx.color('gray', 4, True)}",
    )


def unusual_charges() -> rx.Component:
    return rx.cond(
        StatsState.unusual.length() > 0,
        card(
            rx.vstack(rx.foreach(StatsState.unusual, _row), spacing="0", width="100%"),
            title="Cargos inusuales (últimas semanas)",
        ),
    )
