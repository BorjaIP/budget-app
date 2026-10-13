from collections import defaultdict
import logging
from datetime import datetime

import pydantic
import reflex as rx

from dashboard.anomalies import UnusualRow, find_unusual
from dashboard.database.operations import db_manager
from dashboard.expenses.state import TableState
from dashboard.periods import DEFAULT_PRESET, PRESETS, delta_percent, resolve_period

logger = logging.getLogger(__name__)

_MONTH_ABBR_ES = {
    "01": "ene", "02": "feb", "03": "mar", "04": "abr", "05": "may", "06": "jun",
    "07": "jul", "08": "ago", "09": "sep", "10": "oct", "11": "nov", "12": "dic",
}


class ConceptRow(pydantic.BaseModel):
    concept: str = ""
    total: float = 0.0
    total_fmt: str = ""
    count: int = 0


class RecentRow(pydantic.BaseModel):
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
    available_years: list[str] = []
    period: str = DEFAULT_PRESET
    prev_income: float | None = None
    prev_spending: float | None = None
    review_count: int = 0
    latest_date: str = ""
    daily_mode: bool = False
    unusual: list[UnusualRow] = []
    data_range_label: str = ""
    chart_data: list[dict] = []
    category_breakdown: list[dict] = []
    top_concepts: list[ConceptRow] = []
    recent_expenses: list[RecentRow] = []
    is_loading: bool = False
    load_error: bool = False

    @rx.var(cache=True)
    def preset_value(self) -> str:
        return self.period if self.period in PRESETS else ""

    @rx.var(cache=True)
    def year_value(self) -> str:
        return self.period if self.period.isdigit() else ""

    @rx.event
    async def load_chart_data(self):
        self.is_loading = True
        self.load_error = False
        try:
            self.available_years = db_manager.get_available_years()
            min_date, max_date = db_manager.get_date_bounds()
            self.data_range_label = _format_range_label(min_date, max_date)
            self.latest_date = max_date or ""

            period = resolve_period(self.period, max_date)
            date_from, date_to = period.date_from, period.date_to
            expenses = db_manager.get_all_expenses()

            # Daily buckets when a single month is selected, monthly otherwise
            # (a full year of daily points overlaps and becomes unreadable).
            monthly = not period.daily
            self.daily_mode = period.daily

            income: dict[str, float] = defaultdict(float)
            spending: dict[str, float] = defaultdict(float)
            balance: dict[str, float] = {}

            for expense in expenses:
                op_date = expense.operation_date
                if date_from and op_date < date_from:
                    continue
                if date_to and op_date > date_to:
                    continue
                bucket = op_date[:7] if monthly else op_date
                if expense.amount > 0:
                    income[bucket] += expense.amount
                else:
                    spending[bucket] += abs(expense.amount)
                # expenses are ordered newest-first, so the first hit per
                # bucket is already its most recent balance.
                if bucket not in balance:
                    balance[bucket] = expense.balance

            all_buckets = sorted(set(income) | set(spending) | set(balance))
            humanize = _humanize_month if monthly else _humanize
            self.chart_data = [
                {
                    "date": humanize(b),
                    "income": round(income.get(b, 0.0), 2),
                    "spending": round(spending.get(b, 0.0), 2),
                    "balance": round(balance.get(b, 0.0), 2),
                }
                for b in all_buckets
            ]

            if period.prev_from:
                previous = db_manager.get_flow_totals(period.prev_from, period.prev_to)
                self.prev_income = previous["income"]
                self.prev_spending = previous["spending"]
            else:
                self.prev_income = self.prev_spending = None
            self.review_count = db_manager.count_to_review()
            self.unusual = find_unusual(expenses, max_date)

            breakdown = db_manager.get_category_breakdown(date_from=date_from, date_to=date_to)
            breakdown_total = sum(row["value"] for row in breakdown) or 1.0
            breakdown_peak = max((row["value"] for row in breakdown), default=0.0) or 1.0
            self.category_breakdown = [
                {
                    "name": row["name"],
                    "value": row["value"],
                    "value_fmt": _format_currency(row["value"]),
                    "percent_fmt": f"{row['value'] / breakdown_total * 100:.1f} %".replace(".", ","),
                    "bar": f"{row['value'] / breakdown_peak * 100:.1f}%",
                }
                for row in breakdown
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
                    amount_fmt=("+" if e.amount > 0 else "") + _format_currency(e.amount),
                    category=e.category or "Sin categorizar",
                    is_expense=e.amount < 0,
                )
                for e in db_manager.get_recent_expenses(limit=8)
            ]
        except Exception:
            logger.exception("Could not load the dashboard data")
            self.load_error = True
            self.chart_data = []
            self.category_breakdown = []
            self.top_concepts = []
            self.recent_expenses = []
            self.unusual = []
        finally:
            self.is_loading = False

    @rx.var(cache=True)
    def total_income(self) -> float:
        return sum(d.get("income", 0) for d in self.chart_data)

    @rx.var(cache=True)
    def total_spending(self) -> float:
        return sum(d.get("spending", 0) for d in self.chart_data)

    @rx.var(cache=True)
    def total_income_fmt(self) -> str:
        return _format_currency(self.total_income)

    @rx.var(cache=True)
    def total_spending_fmt(self) -> str:
        return _format_currency(self.total_spending)

    @rx.var(cache=True)
    def net_balance_fmt(self) -> str:
        if not self.chart_data:
            return _format_currency(0.0)
        return _format_currency(self.chart_data[-1].get("balance", 0))

    @rx.var(cache=True)
    def savings_rate_fmt(self) -> str:
        if self.total_income <= 0:
            return "-"
        rate = (self.total_income - self.total_spending) / self.total_income * 100
        return f"{rate:.1f} %".replace(".", ",")

    @rx.var(cache=True)
    def spending_avg(self) -> float:
        spent = [d["spending"] for d in self.chart_data if d.get("spending", 0) > 0]
        return round(sum(spent) / len(spent), 2) if spent else 0.0

    @rx.var(cache=True)
    def spending_avg_line(self) -> int:
        """Whole euros: the reference line only accepts str or int."""
        return round(self.spending_avg)

    @rx.var(cache=True)
    def chart_summary(self) -> str:
        """Text alternative for the income vs spending chart."""
        spent = [d for d in self.chart_data if d.get("spending", 0) > 0]
        if not spent:
            return ""
        unit = "día" if self.daily_mode else "mes"
        peak = max(spent, key=lambda d: d["spending"])
        return (
            f"La línea punteada marca el gasto medio por {unit}: {_format_currency(self.spending_avg)}. "
            f"El más alto fue {peak['date']} con {_format_currency(peak['spending'])}."
        )

    @rx.var(cache=True)
    def income_delta(self) -> str:
        return _delta_label(self.total_income, self.prev_income)

    @rx.var(cache=True)
    def spending_delta(self) -> str:
        return _delta_label(self.total_spending, self.prev_spending)

    @rx.var(cache=True)
    def review_label(self) -> str:
        n = self.review_count
        noun = "movimiento" if n == 1 else "movimientos"
        return f"{n} {noun} por revisar (sin categoría o con poca confianza del modelo)"

    @rx.event
    async def set_period(self, value: str | list[str]):
        chosen = value if isinstance(value, str) else (value[0] if value else "")
        if not chosen:
            return
        self.period = chosen
        await self.load_chart_data()

    @rx.event
    def open_category(self, category: str):
        """Jump to Gastos filtered by this category and the current period."""
        period = resolve_period(self.period, self.latest_date or None)
        return [
            TableState.drill_down(category, period.date_from or "", period.date_to or "", "expense"),
            rx.redirect("/expenses"),
        ]

    @rx.event
    def open_concept(self, concept: str):
        """Jump to Gastos searching this concept within the current period."""
        period = resolve_period(self.period, self.latest_date or None)
        return [
            TableState.drill_down_search(concept, period.date_from or "", period.date_to or ""),
            rx.redirect("/expenses"),
        ]

    @rx.event
    def review_pending(self):
        return [
            TableState.drill_down_review,
            rx.redirect("/expenses"),
        ]


def _delta_label(current: float, previous: float | None) -> str:
    change = None if previous is None else delta_percent(current, previous)
    if change is None:
        return ""
    sign = "+" if change > 0 else "−" if change < 0 else ""
    return f"{sign}{abs(change):.1f} % vs periodo anterior".replace(".", ",")


def _humanize(iso_date: str) -> str:
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso_date


def _humanize_month(bucket: str) -> str:
    try:
        year, month = bucket.split("-")
        return f"{_MONTH_ABBR_ES.get(month, month)} {year}"
    except ValueError:
        return bucket


def _format_range_label(min_date: str | None, max_date: str | None) -> str:
    if not min_date or not max_date:
        return "Sin datos cargados todavía"
    return f"Datos disponibles: {_humanize(min_date)} a {_humanize(max_date)}"


_Y_TICK_FORMATTER = (
    "(value) => {"
    "  const fmt = (n) => n.toFixed(1).replace('.', ',').replace(',0', '');"
    "  const abs = Math.abs(value);"
    "  if (abs >= 1000000) return fmt(value / 1000000) + ' M €';"
    "  if (abs >= 1000) return fmt(value / 1000) + ' k €';"
    "  return value + ' €';"
    "}"
)

_CHART_HEIGHT = 280


def _custom_tooltip():
    return rx.recharts.graphing_tooltip(
        separator=": ",
        content_style={
            "backgroundColor": "var(--color-panel-solid)",
            "borderRadius": "var(--radius-3)",
            "border": "1px solid var(--gray-a6)",
            "padding": "0.5rem 0.75rem",
            "boxShadow": "none",
            "fontSize": "12px",
        },
        is_animation_active=False,
    )


def _x_axis(data_key: str = "date"):
    return rx.recharts.x_axis(
        data_key=data_key,
        tick_line=False,
        axis_line=False,
        interval="preserveStartEnd",
        min_tick_gap=40,
        tick_margin=8,
    )


def _y_axis():
    return rx.recharts.y_axis(
        tick_formatter=_Y_TICK_FORMATTER,
        width=64,
        tick_line=False,
        axis_line=False,
    )


def _empty_chart_placeholder() -> rx.Component:
    return rx.center(
        rx.text(
            "No hay datos para el periodo seleccionado",
            size="2",
            color=rx.color("gray", 11),
        ),
        height="200px",
    )


def _loading_placeholder() -> rx.Component:
    return rx.skeleton(height=f"{_CHART_HEIGHT}px", width="100%")


def date_filter_controls() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.segmented_control.root(
                *[rx.segmented_control.item(label, value=key) for key, label in PRESETS.items()],
                value=StatsState.preset_value,
                on_change=StatsState.set_period,
                size="2",
                custom_attrs={"aria-label": "Periodo"},
            ),
            rx.select(
                StatsState.available_years,
                placeholder="Otro año",
                value=StatsState.year_value,
                on_change=StatsState.set_period,
                size="2",
                custom_attrs={"aria-label": "Año concreto"},
            ),
            spacing="3",
            align="center",
            wrap="wrap",
        ),
        rx.text(StatsState.data_range_label, size="1", color=rx.color("gray", 11)),
        spacing="2",
        align=rx.breakpoints(initial="start", md="end"),
    )


def income_spending_chart() -> rx.Component:
    return rx.cond(
        StatsState.is_loading,
        _loading_placeholder(),
        rx.cond(
            StatsState.chart_data.length() == 0,
            _empty_chart_placeholder(),
            rx.vstack(
                rx.box(
                    rx.recharts.bar_chart(
                        _custom_tooltip(),
                        rx.recharts.cartesian_grid(horizontal=True, vertical=False),
                        rx.recharts.bar(name="Ingresos", data_key="income", fill=rx.color("green", 9)),
                        rx.recharts.bar(name="Gastos", data_key="spending", fill=rx.color("red", 9)),
                        rx.recharts.reference_line(
                            y=StatsState.spending_avg_line,
                            stroke=rx.color("gray", 10),
                            stroke_dasharray="4 4",
                        ),
                        _x_axis(),
                        _y_axis(),
                        rx.recharts.legend(icon_type="circle", icon_size=8),
                        data=StatsState.chart_data,
                        height=_CHART_HEIGHT,
                        bar_gap=2,
                    ),
                    width="100%",
                    custom_attrs={"role": "img", "aria-label": "Ingresos y gastos por periodo. " + StatsState.chart_summary},
                ),
                rx.text(StatsState.chart_summary, size="1", color=rx.color("gray", 11)),
                spacing="2",
                width="100%",
            ),
        ),
    )


def balance_chart() -> rx.Component:
    return rx.cond(
        StatsState.is_loading,
        _loading_placeholder(),
        rx.cond(
            StatsState.chart_data.length() == 0,
            _empty_chart_placeholder(),
            rx.recharts.area_chart(
                _custom_tooltip(),
                rx.recharts.cartesian_grid(horizontal=True, vertical=False),
                rx.recharts.area(
                    name="Saldo",
                    data_key="balance",
                    stroke=rx.color("gray", 12),
                    stroke_width=1.5,
                    fill=rx.color("gray", 4, True),
                    type_="monotone",
                    dot=False,
                ),
                _x_axis(),
                _y_axis(),
                rx.recharts.legend(icon_type="circle", icon_size=8),
                data=StatsState.chart_data,
                height=_CHART_HEIGHT,
            ),
        ),
    )
