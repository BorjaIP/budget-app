import reflex as rx

from dashboard.expenses.state import TableState
from dashboard.expenses.view import main_table
from dashboard.templates import template


@template(route="/expenses", title="Gastos", on_load=TableState.load_entries_from_database)
def expenses() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("Gastos", size="6"),
            rx.spacer(),
            rx.button(
                rx.icon("sparkles", size=16),
                "Recategorizar",
                variant="surface",
                size="2",
                on_click=TableState.force_recategorize,
            ),
            align="center",
            wrap="wrap",
            width="100%",
        ),
        main_table(),
        spacing="4",
        width="100%",
    )
