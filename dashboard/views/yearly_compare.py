import pydantic
import reflex as rx

from dashboard.database.operations import db_manager
from dashboard.views.charts import _Y_TICK_FORMATTER, _custom_tooltip, _format_currency


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

    @rx.event
    async def load_yearly_summary(self):
        self.is_loading = True
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
                    savings_rate_fmt=f"{r['savings_rate']:.1f}%",
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
        except Exception as exc:
            print(f"Error loading yearly summary: {exc}")
            self.rows = []
            self.chart_data = []
        finally:
            self.is_loading = False


def yearly_compare_chart() -> rx.Component:
    return rx.cond(
        YearlyCompareState.chart_data.length() == 0,
        rx.center(
            rx.vstack(
                rx.icon("calendar-range", size=32, color="gray"),
                rx.text("Todavía no hay años completos para comparar", size="3", color="gray"),
                spacing="2",
                align="center",
            ),
            height="300px",
        ),
        rx.recharts.bar_chart(
            _custom_tooltip("teal"),
            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
            rx.recharts.bar(name="Ingresos", data_key="ingresos", fill=rx.color("green", 9)),
            rx.recharts.bar(name="Gastos", data_key="gastos", fill=rx.color("red", 9)),
            rx.recharts.bar(name="Ahorro", data_key="ahorro", fill=rx.color("teal", 9)),
            rx.recharts.x_axis(data_key="year"),
            rx.recharts.y_axis(tick_formatter=_Y_TICK_FORMATTER),
            rx.recharts.legend(),
            data=YearlyCompareState.chart_data,
            height=320,
        ),
    )


def _table_row(row: YearRow) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row.year, weight="medium")),
        rx.table.cell(rx.text(row.ingresos_fmt, color=rx.color("green", 11))),
        rx.table.cell(rx.text(row.gastos_fmt, color=rx.color("red", 11))),
        rx.table.cell(rx.text(row.ahorro_fmt, weight="medium")),
        rx.table.cell(rx.text(row.savings_rate_fmt)),
    )


def yearly_compare_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Año"),
                rx.table.column_header_cell("Ingresos"),
                rx.table.column_header_cell("Gastos"),
                rx.table.column_header_cell("Ahorro"),
                rx.table.column_header_cell("Tasa de ahorro"),
            ),
        ),
        rx.table.body(
            rx.foreach(YearlyCompareState.rows, _table_row),
        ),
        width="100%",
        variant="surface",
    )
