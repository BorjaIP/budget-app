import asyncio
import datetime
import random

import httpx
import reflex as rx
from psutil import users
from reflex.components.radix.themes.base import LiteralAccentColor

from dashboard.expenses.state import TableState
from dashboard.utils.file_reader import FileReader
from dashboard.database.operations import db_manager

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
    is_loading: bool = False

    @rx.event
    def set_selected_tab(self, tab: str | list[str]):
        self.selected_tab = tab if isinstance(tab, str) else tab[0]

    @rx.event
    def toggle_areachart(self):
        self.area_toggle = not self.area_toggle

    @rx.event
    async def refresh_data(self):
        """Refresh chart data"""
        self.is_loading = True
        self.users_data = []  # Clear existing data
        await self.randomize_data()  # Reload data
        self.is_loading = False

    # get_data from FileReader
    async def randomize_data(self):
        # If data is already populated, don't randomize
        if self.users_data:
            return
        
        self.is_loading = True

        try:
            # Load data from database instead of file
            db_expenses = db_manager.get_all_expenses()
            
            if not db_expenses:
                print("No data found in database for charts")
                self.users_data = []
                return
            
            # Convert database expenses to records format
            records = []
            for expense in db_expenses:
                record = {
                    'operation_date': expense.operation_date,
                    'value_date': expense.value_date,
                    'concept': expense.concept,
                    'amount': expense.amount,
                    'salary': expense.salary
                }
                records.append(record)
            
            if records:
                # Process and format data for charts using FileReader conversion
                file_reader = FileReader()  # Create instance for number conversion
                processed_data = []
                for record in records:
                    try:
                        # Use FileReader method to convert European numbers to float for charts
                        salary_value = file_reader.convert_european_number_to_float(record.get('salary', 0))
                        amount_value = file_reader.convert_european_number_to_float(record.get('amount', 0))
                        
                        # Format operation_date if needed
                        operation_date = str(record.get('operation_date', ''))
                        
                        processed_record = {
                            'operation_date': operation_date,
                            'value_date': str(record.get('value_date', '')),
                            'concept': str(record.get('concept', '')),
                            'amount': amount_value,
                            'salary': salary_value
                        }
                        processed_data.append(processed_record)
                    except (ValueError, TypeError) as e:
                        print(f"Skipping record due to formatting error: {e}")
                        continue
                
                self.users_data = processed_data
                print(f"Loaded {len(self.users_data)} records for charts")
                if len(processed_data) > 0:
                    print(f"Sample record: {processed_data[0]}")
                    print(f"Total records with valid salary: {len([r for r in processed_data if r['salary'] != 0])}")
                
                # Also populate revenue_data for potential future use
                self.revenue_data = []
                self.orders_data = []
            else:
                print("No data found for charts")
                self.users_data = []
                
        except Exception as e:
            print(f"Error loading chart data: {e}")
            self.users_data = []
        finally:
            self.is_loading = False

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
        StatsState.is_loading,
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Loading chart data...", size="2", color="gray"),
                spacing="3",
                align="center",
            ),
            height="425px",
        ),
        rx.cond(
            StatsState.users_data == [],
            rx.center(
                rx.vstack(
                    rx.icon("chart-no-axes-combined", size=32, color="gray"),
                    rx.text("No data available", size="4", weight="medium"),
                    rx.text("Click 'Refresh Data' to load chart data", size="2", color="gray"),
                    spacing="3",
                    align="center",
                ),
                height="425px",
            ),
            rx.cond(
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
            ),
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
