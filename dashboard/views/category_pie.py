import reflex as rx

from dashboard.components.category_badge import CATEGORY_COLORS
from dashboard.views.charts import StatsState


def category_pie() -> rx.Component:
    pie_cells = [
        rx.recharts.cell(fill=rx.color(color, 9))
        for _, color in CATEGORY_COLORS.items()
    ]
    pie_cells.append(rx.recharts.cell(fill=rx.color("gray", 8)))

    return rx.cond(
        StatsState.category_breakdown.length() == 0,
        rx.center(
            rx.vstack(
                rx.icon("pie-chart", size=32, color="gray"),
                rx.text("Sin gastos categorizados todavía", size="3", color="gray"),
                spacing="2",
                align="center",
            ),
            height="280px",
        ),
        rx.recharts.pie_chart(
            rx.recharts.graphing_tooltip(),
            rx.recharts.legend(layout="vertical", vertical_align="middle", align="right"),
            rx.recharts.pie(
                *pie_cells,
                data=StatsState.category_breakdown,
                data_key="value",
                name_key="name",
                inner_radius="55%",
                outer_radius="80%",
                padding_angle=2,
            ),
            data=StatsState.category_breakdown,
            height=280,
        ),
    )
