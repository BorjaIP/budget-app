"""Year-over-year comparison page."""

import reflex as rx

from .. import styles
from ..templates import template
from ..views.yearly_compare import (
    YearlyCompareState,
    yearly_compare_chart,
    yearly_compare_table,
)


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


@template(route="/comparativa", title="Comparativa", on_load=YearlyCompareState.load_yearly_summary)
def comparativa() -> rx.Component:
    return rx.vstack(
        rx.heading("Comparativa anual", size="6"),
        rx.text(
            "Ingresos, gastos y ahorro totales de cada año cargado.",
            size="2",
            color=rx.color("gray", 10),
        ),
        _card(yearly_compare_chart(), title="Ingresos vs gastos vs ahorro por año", icon="bar-chart-3"),
        _card(yearly_compare_table(), title="Detalle por año", icon="table"),
        spacing="6",
        width="100%",
    )
