from collections import defaultdict
from datetime import datetime, timedelta

import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

from dashboard.database.operations import db_manager


class ConceptRow(rx.Base):
    concept: str = ""
    total: float = 0.0
    total_fmt: str = ""
    count: int = 0


class RecentRow(rx.Base):
    id: int = 0
    operation_date: str = ""
    concept: str = ""
    amount: float = 0.0
    amount_fmt: str = ""
    category: str = ""
    is_expense: bool = False


def _format_currency(value: float) -> str:
    """Format float as Spanish euro: 1.234,56 €."""
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


class StatsState(rx.State):
    date_filter: str = "all"
    chart_data: list[dict] = []
    category_breakdown: list[dict] = []
    top_concepts: list[ConceptRow] = []
    recent_expenses: list[RecentRow] = []
    is_loading: bool = False

    def _date_range(self) -> tuple[str | None, str | None]:
        now = datetime.now()
        if self.date_filter == "1m":
            start = now - timedelta(days=30)
        elif self.date_filter == "6m":
            start = now - timedelta(days=180)
        elif self.date_filter == "1y":
            start = now - timedelta(days=365)
        else:
            return None, None
        return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")

    @rx.event
    async def load_chart_data(self):
        self.is_loading = True
        try:
            date_from, date_to = self._date_range()
            expenses = db_manager.get_all_expenses()

            ingresos: dict[str, float] = defaultdict(float)
            gastos: dict[str, float] = defaultdict(float)
            saldo: dict[str, float] = {}

            for expense in expenses:
                op_date = expense.operation_date
                if date_from and op_date < date_from:
                    continue
                if date_to and op_date > date_to:
                    continue
                if expense.amount > 0:
                    ingresos[op_date] += expense.amount
                else:
                    gastos[op_date] += abs(expense.amount)
                saldo[op_date] = expense.balance

            all_dates = sorted(set(ingresos) | set(gastos) | set(saldo))
            self.chart_data = [
                {
                    "date": _humanize(d),
                    "ingresos": round(ingresos.get(d, 0.0), 2),
                    "gastos": round(gastos.get(d, 0.0), 2),
                    "saldo": round(saldo.get(d, 0.0), 2),
                }
                for d in all_dates
            ]

            self.category_breakdown = [
                {
                    "name": row["name"],
                    "value": row["value"],
                    "value_fmt": _format_currency(row["value"]),
                }
                for row in db_manager.get_category_breakdown(
                    date_from=date_from, date_to=date_to
                )
            ]
            self.top_concepts = [
                ConceptRow(
                    concept=row["concept"],
                    total=row["total"],
                    total_fmt=_format_currency(row["total"]),
                    count=row["count"],
                )
                for row in db_manager.get_top_concepts(
                    limit=8, date_from=date_from, date_to=date_to
                )
            ]
            self.recent_expenses = [
                RecentRow(
                    id=e.id or 0,
                    operation_date=_humanize(e.operation_date),
                    concept=e.concept,
                    amount=e.amount,
                    amount_fmt=_format_currency(e.amount),
                    category=e.category or "Sin categorizar",
                    is_expense=e.amount < 0,
                )
                for e in db_manager.get_recent_expenses(limit=8)
            ]
        except Exception as exc:
            print(f"Error loading chart data: {exc}")
            self.chart_data = []
            self.category_breakdown = []
            self.top_concepts = []
            self.recent_expenses = []
        finally:
            self.is_loading = False

    @rx.var(cache=True)
    def total_ingresos(self) -> float:
        return sum(d.get("ingresos", 0) for d in self.chart_data)

    @rx.var(cache=True)
    def total_gastos(self) -> float:
        return sum(d.get("gastos", 0) for d in self.chart_data)

    @rx.var(cache=True)
    def total_ingresos_fmt(self) -> str:
        return _format_currency(self.total_ingresos)

    @rx.var(cache=True)
    def total_gastos_fmt(self) -> str:
        return _format_currency(self.total_gastos)

    @rx.var(cache=True)
    def saldo_neto_fmt(self) -> str:
        if not self.chart_data:
            return _format_currency(0.0)
        return _format_currency(self.chart_data[-1].get("saldo", 0))

    @rx.var(cache=True)
    def savings_rate_fmt(self) -> str:
        if self.total_ingresos <= 0:
            return "—"
        rate = (self.total_ingresos - self.total_gastos) / self.total_ingresos * 100
        return f"{rate:.1f}%"

    @rx.var(cache=True)
    def savings_rate_color(self) -> str:
        if self.total_ingresos <= 0:
            return "gray"
        rate = (self.total_ingresos - self.total_gastos) / self.total_ingresos * 100
        if rate >= 20:
            return "green"
        if rate > 0:
            return "amber"
        return "red"

    @rx.event
    async def set_date_preset(self, value: str | list[str]):
        self.date_filter = value if isinstance(value, str) else value[0]
        await self.load_chart_data()


def _humanize(iso_date: str) -> str:
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso_date


_Y_TICK_FORMATTER = rx.Var(
    "(value) => {"
    "  if (Math.abs(value) >= 1000000) return (value / 1000000).toFixed(1) + 'M €';"
    "  if (Math.abs(value) >= 1000) return (value / 1000).toFixed(1) + 'K €';"
    "  return value + ' €';"
    "}"
)


def _create_gradient(color: LiteralAccentColor, gradient_id: str):
    return rx.el.svg.defs(
        rx.el.svg.linear_gradient(
            rx.el.svg.stop(stop_color=rx.color(color, 7), offset="5%", stop_opacity=0.8),
            rx.el.svg.stop(stop_color=rx.color(color, 7), offset="95%", stop_opacity=0),
            x1=0, x2=0, y1=0, y2=1,
            id=gradient_id,
        ),
    )


def _custom_tooltip(color: LiteralAccentColor):
    return rx.recharts.graphing_tooltip(
        separator=" : ",
        content_style={
            "backgroundColor": rx.color("gray", 1),
            "borderRadius": "var(--radius-2)",
            "borderWidth": "1px",
            "borderColor": rx.color(color, 7),
            "padding": "0.5rem",
            "boxShadow": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
        },
        is_animation_active=True,
    )


def _empty_chart_placeholder() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon("chart-no-axes-combined", size=32, color="gray"),
            rx.text("No hay datos para el periodo seleccionado", size="3", weight="medium"),
            spacing="3",
            align="center",
        ),
        height="300px",
    )


def _loading_placeholder() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.spinner(size="3"),
            rx.text("Cargando datos...", size="2", color="gray"),
            spacing="3",
            align="center",
        ),
        height="300px",
    )


def date_filter_controls() -> rx.Component:
    return rx.hstack(
        rx.segmented_control.root(
            rx.segmented_control.item("Todo", value="all"),
            rx.segmented_control.item("1 mes", value="1m"),
            rx.segmented_control.item("6 meses", value="6m"),
            rx.segmented_control.item("1 año", value="1y"),
            value=StatsState.date_filter,
            on_change=StatsState.set_date_preset,
        ),
        spacing="4",
        align="center",
        wrap="wrap",
    )


def ingresos_gastos_chart() -> rx.Component:
    return rx.cond(
        StatsState.is_loading,
        _loading_placeholder(),
        rx.cond(
            StatsState.chart_data.length() == 0,
            _empty_chart_placeholder(),
            rx.recharts.bar_chart(
                _custom_tooltip("teal"),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.bar(
                    name="Ingresos",
                    data_key="ingresos",
                    fill=rx.color("green", 9),
                ),
                rx.recharts.bar(
                    name="Gastos",
                    data_key="gastos",
                    fill=rx.color("red", 9),
                ),
                rx.recharts.x_axis(data_key="date", scale="auto"),
                rx.recharts.y_axis(tick_formatter=_Y_TICK_FORMATTER),
                rx.recharts.legend(),
                data=StatsState.chart_data,
                height=300,
            ),
        ),
    )


def saldo_chart() -> rx.Component:
    return rx.cond(
        StatsState.is_loading,
        _loading_placeholder(),
        rx.cond(
            StatsState.chart_data.length() == 0,
            _empty_chart_placeholder(),
            rx.recharts.area_chart(
                _create_gradient("blue", "colorBlue"),
                _custom_tooltip("blue"),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.area(
                    name="Saldo",
                    data_key="saldo",
                    stroke=rx.color("blue", 9),
                    fill="url(#colorBlue)",
                    type_="monotone",
                ),
                rx.recharts.x_axis(data_key="date", scale="auto"),
                rx.recharts.y_axis(tick_formatter=_Y_TICK_FORMATTER),
                rx.recharts.legend(),
                data=StatsState.chart_data,
                height=300,
            ),
        ),
    )
