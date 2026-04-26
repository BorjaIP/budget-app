from collections import defaultdict
from datetime import datetime, timedelta

import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

from dashboard.database.operations import db_manager
from dashboard.utils.file_reader import FileReader


class StatsState(rx.State):
    date_filter: str = "all"
    chart_data: list[dict] = []
    is_loading: bool = False

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse dd/mm/yyyy date string."""
        try:
            return datetime.strptime(date_str.strip(), "%d/%m/%Y")
        except (ValueError, AttributeError):
            return None

    def _get_date_range(self) -> tuple[datetime | None, datetime | None]:
        """Compute start/end dates based on current filter."""
        now = datetime.now()
        if self.date_filter == "1m":
            return now - timedelta(days=30), now
        elif self.date_filter == "6m":
            return now - timedelta(days=180), now
        elif self.date_filter == "1y":
            return now - timedelta(days=365), now
        else:  # "all"
            return None, None

    @rx.event
    async def load_chart_data(self):
        """Load expenses from DB, aggregate by date into ingresos/gastos/saldo."""
        self.is_loading = True
        try:
            db_expenses = db_manager.get_all_expenses()
            if not db_expenses:
                self.chart_data = []
                return

            file_reader = FileReader()
            date_start, date_end = self._get_date_range()

            # Parse and filter records
            parsed: list[tuple[datetime, float, float]] = []
            for exp in db_expenses:
                dt = self._parse_date(exp.operation_date)
                if dt is None:
                    continue
                if date_start and dt < date_start:
                    continue
                if date_end and dt > date_end:
                    continue
                amount = file_reader.convert_european_number_to_float(exp.amount)
                salary = file_reader.convert_european_number_to_float(exp.salary)
                parsed.append((dt, amount, salary))

            if not parsed:
                self.chart_data = []
                return

            # Aggregate by date
            ingresos: dict[str, float] = defaultdict(float)
            gastos: dict[str, float] = defaultdict(float)
            saldo: dict[str, float] = {}

            for dt, amount, salary in parsed:
                key = dt.strftime("%d/%m/%Y")
                if amount > 0:
                    ingresos[key] += amount
                else:
                    gastos[key] += abs(amount)
                # Keep last saldo for each date
                saldo[key] = salary

            # Build sorted result
            all_dates = set(ingresos.keys()) | set(gastos.keys()) | set(saldo.keys())
            result = []
            for date_str in all_dates:
                dt = datetime.strptime(date_str, "%d/%m/%Y")
                result.append({
                    "date": date_str,
                    "_sort": dt.timestamp(),
                    "ingresos": round(ingresos.get(date_str, 0), 2),
                    "gastos": round(gastos.get(date_str, 0), 2),
                    "saldo": round(saldo.get(date_str, 0), 2),
                })

            result.sort(key=lambda r: r["_sort"])
            # Remove sort key before sending to frontend
            for r in result:
                del r["_sort"]

            self.chart_data = result
        except Exception as e:
            print(f"Error loading chart data: {e}")
            self.chart_data = []
        finally:
            self.is_loading = False

    @rx.var(cache=True)
    def total_ingresos_fmt(self) -> str:
        total = sum(d.get("ingresos", 0) for d in self.chart_data)
        return f"{total:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var(cache=True)
    def total_gastos_fmt(self) -> str:
        total = sum(d.get("gastos", 0) for d in self.chart_data)
        return f"{total:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var(cache=True)
    def saldo_neto_fmt(self) -> str:
        if not self.chart_data:
            return "0,00 €"
        last = self.chart_data[-1].get("saldo", 0)
        return f"{last:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.event
    async def set_date_preset(self, value: str | list[str]):
        """Set a date filter preset and reload data."""
        self.date_filter = value if isinstance(value, str) else value[0]
        await self.load_chart_data()



# ---------------------------------------------------------------------------
# Reusable chart helpers
# ---------------------------------------------------------------------------

_Y_TICK_FORMATTER = rx.Var(
    "(value) => {"
    "  if (Math.abs(value) >= 1000000) return (value / 1000000).toFixed(1) + 'M €';"
    "  if (Math.abs(value) >= 1000) return (value / 1000).toFixed(1) + 'K €';"
    "  return value + ' €';"
    "}"
)


def _create_gradient(color: LiteralAccentColor, id: str):
    """Create a gradient for area charts."""
    return rx.el.svg.defs(
        rx.el.svg.linear_gradient(
            rx.el.svg.stop(stop_color=rx.color(color, 7), offset="5%", stop_opacity=0.8),
            rx.el.svg.stop(stop_color=rx.color(color, 7), offset="95%", stop_opacity=0),
            x1=0, x2=0, y1=0, y2=1,
            id=id,
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
            rx.text("No hay datos disponibles", size="4", weight="medium"),
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


# ---------------------------------------------------------------------------
# Date filter controls
# ---------------------------------------------------------------------------

def date_filter_controls() -> rx.Component:
    return rx.hstack(
        rx.segmented_control.root(
            rx.segmented_control.item("Todo", value="all"),
            rx.segmented_control.item("1 Mes", value="1m"),
            rx.segmented_control.item("6 Meses", value="6m"),
            rx.segmented_control.item("1 Ano", value="1y"),
            value=StatsState.date_filter,
            on_change=StatsState.set_date_preset,
        ),
        spacing="4",
        align="center",
        wrap="wrap",
    )


# ---------------------------------------------------------------------------
# Three chart components
# ---------------------------------------------------------------------------

def ingresos_chart() -> rx.Component:
    return rx.cond(
        StatsState.is_loading,
        _loading_placeholder(),
        rx.cond(
            StatsState.chart_data.length() == 0,
            _empty_chart_placeholder(),
            rx.recharts.line_chart(
                _custom_tooltip("green"),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.line(
                    name="Ingresos",
                    data_key="ingresos",
                    stroke=rx.color("green", 9),
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


def gastos_chart() -> rx.Component:
    return rx.cond(
        StatsState.is_loading,
        _loading_placeholder(),
        rx.cond(
            StatsState.chart_data.length() == 0,
            _empty_chart_placeholder(),
            rx.recharts.line_chart(
                _custom_tooltip("red"),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.line(
                    name="Gastos",
                    data_key="gastos",
                    stroke=rx.color("red", 9),
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


def ingresos_gastos_chart() -> rx.Component:
    """Combined bar chart with Ingresos (green) and Gastos (red) side by side."""
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
                    name="Saldo Final",
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
