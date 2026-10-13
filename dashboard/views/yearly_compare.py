import logging

import pydantic
import reflex as rx

from dashboard.database.operations import db_manager
from dashboard.views.charts import (
    _CHART_HEIGHT,
    _Y_TICK_FORMATTER,
    _custom_tooltip,
    _format_currency,
    _x_axis,
)

logger = logging.getLogger(__name__)


class YearRow(pydantic.BaseModel):
    year: str = ""
    ingresos: float = 0.0
    gastos: float = 0.0
    ahorro: float = 0.0
    ingresos_fmt: str = ""
    gastos_fmt: str = ""
    ahorro_fmt: str = ""
    savings_rate: float = 0.0
    savings_rate_fmt: str = ""


class YearlyCompareState(rx.State):
    rows: list[YearRow] = []
    chart_data: list[dict] = []
    is_loading: bool = False
    load_error: bool = False

    @rx.event
    async def load_yearly_summary(self):
        self.is_loading = True
        self.load_error = False
        try:
            summary = db_manager.get_yearly_summary()
            self.rows = [
                YearRow(
                    year=r["year"],
                    ingresos=r["ingresos"],
                    gastos=r["gastos"],
                    ahorro=r["ahorro"],
                    ingresos_fmt=_format_currency(r["ingresos"]),
                    gastos_fmt=_format_currency(r["gastos"]),
                    ahorro_fmt=_format_currency(r["ahorro"]),
                    savings_rate=r["savings_rate"],
                    savings_rate_fmt=f"{r['savings_rate']:.1f} %".replace(".", ","),
                )
                for r in summary
            ]
            self.chart_data = [
                {
                    "year": r["year"],
                    "ingresos": r["ingresos"],
                    "gastos": r["gastos"],
                    "ahorro": r["ahorro"],
                }
                for r in summary
            ]
        except Exception:
            logger.exception("Could not load the yearly summary")
            self.load_error = True
            self.rows = []
            self.chart_data = []
        finally:
            self.is_loading = False


def yearly_compare_chart() -> rx.Component:
    return rx.cond(
        YearlyCompareState.is_loading,
        rx.skeleton(height=f"{_CHART_HEIGHT}px", width="100%"),
        rx.cond(
            YearlyCompareState.chart_data.length() == 0,
            rx.center(
                rx.text(
                    "Todavía no hay años completos para comparar",
                    size="2",
                    color=rx.color("gray", 11),
                ),
                height="200px",
            ),
            rx.recharts.bar_chart(
                _custom_tooltip(),
                rx.recharts.cartesian_grid(horizontal=True, vertical=False),
                rx.recharts.bar(name="Ingresos", data_key="ingresos", fill=rx.color("green", 9)),
                rx.recharts.bar(name="Gastos", data_key="gastos", fill=rx.color("red", 9)),
                rx.recharts.bar(name="Ahorro", data_key="ahorro", fill=rx.color("gray", 12)),
                _x_axis("year"),
                rx.recharts.y_axis(
                    tick_formatter=_Y_TICK_FORMATTER,
                    width=64,
                    tick_line=False,
                    axis_line=False,
                ),
                rx.recharts.legend(icon_type="circle", icon_size=8),
                data=YearlyCompareState.chart_data,
                height=_CHART_HEIGHT,
                bar_gap=2,
            ),
        ),
    )


def _table_row(row: YearRow) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(rx.text(row.year, weight="medium", class_name="num")),
        rx.table.cell(rx.text(row.ingresos_fmt, class_name="num"), justify="end"),
        rx.table.cell(rx.text(row.gastos_fmt, class_name="num"), justify="end"),
        rx.table.cell(
            rx.text(
                row.ahorro_fmt,
                weight="medium",
                class_name="num",
                color=rx.cond(row.ahorro >= 0, rx.color("green", 11), rx.color("red", 11)),
            ),
            justify="end",
        ),
        rx.table.cell(rx.text(row.savings_rate_fmt, class_name="num"), justify="end"),
    )


def yearly_compare_table() -> rx.Component:
    return rx.scroll_area(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Año"),
                    rx.table.column_header_cell("Ingresos", justify="end"),
                    rx.table.column_header_cell("Gastos", justify="end"),
                    rx.table.column_header_cell("Ahorro", justify="end"),
                    rx.table.column_header_cell("Tasa de ahorro", justify="end"),
                ),
            ),
            rx.table.body(
                rx.foreach(YearlyCompareState.rows, _table_row),
            ),
            width="100%",
            min_width="30rem",
            variant="ghost",
        ),
        type="auto",
        scrollbars="horizontal",
        width="100%",
    )
