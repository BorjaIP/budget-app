"""Year-over-year comparison page."""

import reflex as rx

from ..components.card import card
from ..components.notice import error_notice
from ..components.page_header import page_header
from ..templates import template
from ..views.category_trend import CategoryTrendState, category_trend
from ..views.yearly_compare import (
    YearlyCompareState,
    yearly_compare_chart,
    yearly_compare_table,
)


@template(route="/comparativa", title="Comparativa", on_load=[YearlyCompareState.load_yearly_summary, CategoryTrendState.load_trend])
def comparativa() -> rx.Component:
    return rx.vstack(
        page_header(
            "Comparativa anual",
            "Ingresos, gastos y ahorro totales de cada año cargado.",
        ),
        rx.cond(
            YearlyCompareState.load_error,
            error_notice(
                "No se pudo cargar la comparativa.",
                YearlyCompareState.load_yearly_summary,
            ),
        ),
        card(yearly_compare_chart(), title="Ingresos vs gastos vs ahorro por año"),
        card(yearly_compare_table(), title="Detalle por año"),
        card(category_trend(), title="Gasto mensual por categoría"),
        spacing="6",
        width="100%",
    )
