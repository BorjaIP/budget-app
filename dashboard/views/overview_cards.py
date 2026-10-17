"""Cards of the overview: summary sentences, cash flow, categories donut, pace, changes and upcoming charges."""

import reflex as rx

from dashboard.components.card import card
from dashboard.components.icon import icon
from dashboard.views.charts import (
    _CHART_HEIGHT,
    _Y_TICK_FORMATTER,
    _custom_tooltip,
    _x_axis,
    StatsState,
)

_NOTE = {"overflow": "hidden", "text_overflow": "ellipsis", "white_space": "nowrap"}


def insights_card() -> rx.Component:
    return rx.cond(
        StatsState.insight_lines.length() > 0,
        card(
            rx.vstack(
                rx.foreach(
                    StatsState.insight_lines,
                    lambda line: rx.hstack(
                        icon("check", size=14, color=rx.color("gray", 10)),
                        rx.text(line, size="2"),
                        spacing="2",
                        align="start",
                    ),
                ),
                spacing="2",
                align="start",
            ),
            title="En resumen",
        ),
    )


def cashflow_card() -> rx.Component:
    return card(
        rx.cond(
            StatsState.sankey_svg != "",
            rx.box(rx.html(StatsState.sankey_svg), width="100%", overflow_x="auto"),
            rx.center(
                rx.text("Aún no hay movimientos en este periodo", size="2", color=rx.color("gray", 11)),
                height="200px",
            ),
        ),
        title="Flujo de caja",
        subtitle="De dónde viene el dinero y a dónde va",
    )


def _segment_row(segment) -> rx.Component:
    content = rx.hstack(
        rx.box(width="10px", height="10px", border_radius="50%", flex_shrink="0", background=segment["fill"]),
        rx.text(segment["name"], size="2", flex="1", min_width="0", style=_NOTE),
        rx.text(segment["value_fmt"], size="2", weight="medium", class_name="num", style={"white_space": "nowrap"}),
        rx.text(segment["percent_fmt"], size="1", color=rx.color("gray", 11), class_name="num", width="3em", text_align="right"),
        align="center",
        spacing="2",
        width="100%",
        padding_y="0.35rem",
    )
    return rx.cond(
        segment["name"] == "Otras",
        content,
        rx.el.button(
            content,
            type="button",
            on_click=StatsState.open_category(segment["name"]),
            title="Ver estos gastos",
            class_name="row-link",
        ),
    )


def categories_card() -> rx.Component:
    return card(
        rx.cond(
            StatsState.segments.length() == 0,
            rx.center(
                rx.text("Sin gastos categorizados todavía", size="2", color=rx.color("gray", 11)),
                height="200px",
            ),
            rx.vstack(
                rx.center(rx.html(StatsState.donut_svg), width="100%"),
                rx.vstack(rx.foreach(StatsState.segments, _segment_row), spacing="0", width="100%"),
                spacing="3",
                width="100%",
            ),
        ),
        title="Gasto por categoría",
    )


def pace_card() -> rx.Component:
    return rx.cond(
        StatsState.pace_data.length() > 0,
        card(
            rx.recharts.line_chart(
                _custom_tooltip(),
                rx.recharts.cartesian_grid(horizontal=True, vertical=False),
                rx.recharts.line(
                    name="Este periodo", data_key="actual", stroke=rx.color("gray", 12), stroke_width=2, dot=False,
                    is_animation_active=False,
                ),
                rx.recharts.line(
                    name="Periodo anterior", data_key="anterior", stroke=rx.color("gray", 8), stroke_width=2,
                    stroke_dasharray="4 4", dot=False, is_animation_active=False,
                ),
                _x_axis("day"),
                rx.recharts.y_axis(tick_formatter=_Y_TICK_FORMATTER, width=64, tick_line=False, axis_line=False),
                rx.recharts.legend(icon_type="circle", icon_size=8),
                data=StatsState.pace_data,
                height=_CHART_HEIGHT - 60,
            ),
            title="Ritmo de gasto",
            subtitle="Gasto acumulado día a día frente al periodo anterior",
        ),
    )


def _mover_row(row) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(row["name"], size="2", flex="1", min_width="0", style=_NOTE),
            rx.text(row["now_fmt"], size="1", color=rx.color("gray", 11), class_name="num"),
            rx.text(
                row["delta_fmt"],
                size="2",
                weight="medium",
                class_name="num",
                color=rx.cond(row["up"], rx.color("red", 11), rx.color("green", 11)),
                style={"white_space": "nowrap"},
            ),
            align="center",
            spacing="3",
            width="100%",
        ),
        rx.box(
            rx.box(
                width=row["bar"],
                height="100%",
                background=rx.cond(row["up"], rx.color("red", 8), rx.color("green", 8)),
                border_radius="2px",
            ),
            width="100%",
            height="4px",
            background=rx.color("gray", 4, True),
            border_radius="2px",
        ),
        spacing="1",
        width="100%",
        padding_y="0.4rem",
    )


def movers_card() -> rx.Component:
    return rx.cond(
        StatsState.movers_rows.length() > 0,
        card(
            rx.vstack(rx.foreach(StatsState.movers_rows, _mover_row), spacing="1", width="100%"),
            title="Qué ha cambiado",
            subtitle="Categorías con más variación frente al periodo anterior",
        ),
    )


def _upcoming_row(row) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(row.concept, size="2", weight="medium", style=_NOTE, max_width="100%"),
            rx.text(
                "Previsto el " + row.next_date_fmt + rx.cond(row.variable, " · varía cada mes", ""),
                size="1",
                color=rx.color("gray", 11),
            ),
            spacing="0",
            align="start",
            flex="1",
            min_width="0",
        ),
        rx.text(row.estimate_fmt, size="2", weight="medium", class_name="num", style={"white_space": "nowrap"}),
        align="center",
        spacing="3",
        width="100%",
        padding_y="0.5rem",
        border_bottom=f"1px solid {rx.color('gray', 4, True)}",
    )


def upcoming_card() -> rx.Component:
    return rx.cond(
        StatsState.upcoming_rows.length() > 0,
        card(
            rx.vstack(
                rx.foreach(StatsState.upcoming_rows, _upcoming_row),
                rx.hstack(
                    rx.text("Total estimado", size="2", color=rx.color("gray", 11)),
                    rx.spacer(),
                    rx.text(StatsState.upcoming_total_fmt, size="2", weight="medium", class_name="num"),
                    width="100%",
                    padding_top="0.5rem",
                ),
                spacing="0",
                width="100%",
            ),
            title="Próximos cargos",
            subtitle="Lo que suele llegar y todavía no ha llegado este mes",
        ),
    )
