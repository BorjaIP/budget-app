import reflex as rx

from dashboard.components.page_header import page_header
from dashboard.expenses.state import TableState
from dashboard.expenses.view import main_table
from dashboard.templates import template


@template(route="/expenses", title="Gastos", on_load=TableState.load_entries_from_database)
def expenses() -> rx.Component:
    return rx.vstack(
        page_header(
            "Gastos",
            actions=rx.button(
                "Recategorizar",
                variant="soft",
                color_scheme="gray",
                size="2",
                on_click=TableState.force_recategorize,
            ),
        ),
        main_table(),
        spacing="5",
        width="100%",
    )
