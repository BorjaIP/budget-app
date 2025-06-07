import reflex as rx

from dashboard.expenses.state import TableState
from dashboard.expenses.view import TableView
from dashboard.templates import template


@template(route="/expenses", title="Gastos", on_load=TableState.load_entries)  # type: ignore
def expenses() -> rx.Component:
    """The table page.

    Returns:
        The UI for the table page.
    """
    view = TableView()
    return rx.vstack(
        rx.heading("Gastos", size="5"),
        view.main_table(),
        spacing="8",
        width="100%",
    )
