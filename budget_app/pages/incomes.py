import reflex as rx

from budget_app.components.forms import income_form
from budget_app.components.layout import app_layout
from budget_app.components.tables import generic_table
from budget_app.services.income_service import get_all_incomes


def page():
    incomes = get_all_incomes()
    return app_layout(
        rx.vstack(
            rx.heading("Incomes"),
            income_form(),
            generic_table(incomes, ["Date", "Source", "Description", "Amount"]),
        )
    )
