import asyncio
import datetime
import random

import httpx
import reflex as rx
from psutil import users
from reflex.components.radix.themes.base import LiteralAccentColor

from dashboard.expenses.state import TableState

# from dashboard.llm.prompt import PROMPT


class StatsState(rx.State):
    area_toggle: bool = True
    selected_tab: str = "users"
    timeframe: str = "Monthly"
    users_data = []
    revenue_data = []
    orders_data = []
    device_data = []
    yearly_device_data = []

    @rx.event
    def set_selected_tab(self, tab: str | list[str]):
        self.selected_tab = tab if isinstance(tab, str) else tab[0]

    def toggle_areachart(self):
        self.area_toggle = not self.area_toggle

    # get_data from DB
    async def randomize_data(self):
        # If data is already populated, don't randomize

        if self.users_data:
            # result = await query_llm(self.users_data[0]["concept"])
            # print(result)
            return

        # for i in range(30, -1, -1):  # Include today's data
        #     self.revenue_data.append(
        #         {
        #             "Date": (datetime.datetime.now() - datetime.timedelta(days=i)).strftime(
        #                 "%m-%d"
        #             ),
        #             "Revenue": random.randint(1000, 5000),
        #         }
        #     )

        # _ = await query_llm(PROMPT)
        state_expenses = await self.get_state(TableState)
        self.users_data = [item.dict() for item in state_expenses.items]

        # self.device_data = [
        #     {"name": "Desktop", "value": 23, "fill": "var(--blue-8)"},
        #     {"name": "Mobile", "value": 47, "fill": "var(--green-8)"},
        #     {"name": "Tablet", "value": 25, "fill": "var(--purple-8)"},
        #     {"name": "Other", "value": 5, "fill": "var(--red-8)"},
        # ]

        # self.yearly_device_data = [
        #     {"name": "Desktop", "value": 34, "fill": "var(--blue-8)"},
        #     {"name": "Mobile", "value": 46, "fill": "var(--green-8)"},
        #     {"name": "Tablet", "value": 21, "fill": "var(--purple-8)"},
        #     {"name": "Other", "value": 9, "fill": "var(--red-8)"},
        # ]


def area_toggle() -> rx.Component:
    """Toggle between area and bar chart."""
    return rx.cond(
        StatsState.area_toggle,
        rx.icon_button(
            rx.icon("area-chart"),
            size="2",
            cursor="pointer",
            variant="surface",
            on_click=StatsState.toggle_areachart,
        ),
        rx.icon_button(
            rx.icon("bar-chart-3"),
            size="2",
            cursor="pointer",
            variant="surface",
            on_click=StatsState.toggle_areachart,
        ),
    )


def _create_gradient(color: LiteralAccentColor, id: str):
    """Create a gradient for the area chart."""
    return (
        rx.el.svg.defs(
            rx.el.svg.linear_gradient(
                rx.el.svg.stop(stop_color=rx.color(color, 7), offset="5%", stop_opacity=0.8),
                rx.el.svg.stop(stop_color=rx.color(color, 7), offset="95%", stop_opacity=0),
                x1=0,
                x2=0,
                y1=0,
                y2=1,
                id=id,
            ),
        ),
    )


def _custom_tooltip(color: LiteralAccentColor):
    return (
        rx.recharts.graphing_tooltip(
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
        ),
    )


def users_chart() -> rx.Component:
    return rx.cond(
        StatsState.area_toggle,
        rx.recharts.area_chart(
            _create_gradient("blue", "colorBlue"),
            _custom_tooltip("blue"),
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
            ),
            rx.recharts.area(
                name="Saldo",
                data_key="salary",
                stroke=rx.color("blue", 9),
                fill="url(#colorBlue)",
                type_="monotone",
            ),
            rx.recharts.x_axis(data_key="operation_date", scale="auto"),
            rx.recharts.y_axis(),
            rx.recharts.legend(),
            data=StatsState.users_data,
            height=425,
        ),
        rx.recharts.bar_chart(
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
            ),
            _custom_tooltip("blue"),
            rx.recharts.bar(
                name="Saldo",
                data_key="salary",
                stroke=rx.color("blue", 9),
                fill=rx.color("blue", 7),
            ),
            rx.recharts.x_axis(data_key="operation_date", scale="auto"),
            rx.recharts.y_axis(),
            rx.recharts.legend(),
            data=StatsState.users_data,
            height=425,
        ),
    )


def revenue_chart() -> rx.Component:
    return rx.cond(
        StatsState.area_toggle,
        rx.recharts.area_chart(
            _create_gradient("green", "colorGreen"),
            _custom_tooltip("green"),
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
            ),
            rx.recharts.area(
                data_key="Revenue",
                stroke=rx.color("green", 9),
                fill="url(#colorGreen)",
                type_="monotone",
            ),
            rx.recharts.x_axis(data_key="Date", scale="auto"),
            rx.recharts.y_axis(),
            rx.recharts.legend(),
            data=StatsState.revenue_data,
            height=425,
        ),
        rx.recharts.bar_chart(
            _custom_tooltip("green"),
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
            ),
            rx.recharts.bar(
                data_key="Revenue",
                stroke=rx.color("green", 9),
                fill=rx.color("green", 7),
            ),
            rx.recharts.x_axis(data_key="Date", scale="auto"),
            rx.recharts.y_axis(),
            rx.recharts.legend(),
            data=StatsState.revenue_data,
            height=425,
        ),
    )


def orders_chart() -> rx.Component:
    return rx.cond(
        StatsState.area_toggle,
        rx.recharts.area_chart(
            _create_gradient("purple", "colorPurple"),
            _custom_tooltip("purple"),
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
            ),
            rx.recharts.area(
                data_key="Orders",
                stroke=rx.color("purple", 9),
                fill="url(#colorPurple)",
                type_="monotone",
            ),
            rx.recharts.x_axis(data_key="Date", scale="auto"),
            rx.recharts.y_axis(),
            rx.recharts.legend(),
            data=StatsState.orders_data,
            height=425,
        ),
        rx.recharts.bar_chart(
            _custom_tooltip("purple"),
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
            ),
            rx.recharts.bar(
                data_key="Orders",
                stroke=rx.color("purple", 9),
                fill=rx.color("purple", 7),
            ),
            rx.recharts.x_axis(data_key="Date", scale="auto"),
            rx.recharts.y_axis(),
            rx.recharts.legend(),
            data=StatsState.orders_data,
            height=425,
        ),
    )


# def pie_chart() -> rx.Component:
#     return rx.cond(
#         StatsState.timeframe == "Yearly",
#         rx.recharts.pie_chart(
#             rx.recharts.pie(
#                 data=StatsState.yearly_device_data,
#                 data_key="value",
#                 name_key="name",
#                 cx="50%",
#                 cy="50%",
#                 padding_angle=1,
#                 inner_radius="70",
#                 outer_radius="100",
#                 label=True,
#             ),
#             rx.recharts.legend(),
#             height=300,
#         ),
#         rx.recharts.pie_chart(
#             rx.recharts.pie(
#                 data=StatsState.device_data,
#                 data_key="value",
#                 name_key="name",
#                 cx="50%",
#                 cy="50%",
#                 padding_angle=1,
#                 inner_radius="70",
#                 outer_radius="100",
#                 label=True,
#             ),
#             rx.recharts.legend(),
#             height=300,
#         ),
#     )


# def timeframe_select() -> rx.Component:
#     return rx.select(
#         ["Monthly", "Yearly"],
#         default_value="Monthly",
#         value=StatsState.timeframe,
#         variant="surface",
#         on_change=StatsState.set_timeframe,
#     )
