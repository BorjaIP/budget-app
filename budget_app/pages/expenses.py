import reflex as rx

from budget_app.components.forms import expense_form
from budget_app.components.layout import app_layout
from budget_app.components.tables import generic_table
from budget_app.services.expense_service import get_all_expenses

class ExpensePage:
    def __init__(self):
        pass
        # self.expenses = get_all_expenses()

    # def get_expenses(self):
    #     return self.expenses

    def layout(self):
        def index() -> rx.Component:
    return rx.vstack(
        navbar(),
        stats_cards_group(),
        rx.box(
            main_table(),
            width="100%",
        ),
        width="100%",
        spacing="6",
        padding_x=["1.5em", "1.5em", "3em"],
    )
        return app_layout(
            rx.vstack(
                rx.heading("Expenses"),
                expense_form(),
                generic_table(self.expenses, ["Date", "Category", "Description", "Amount"]),
            )
        )

def page():
    # expenses = get_all_expenses()


    return app_layout(
        rx.vstack(
            rx.heading("Expenses"),
            expense_form(),
            generic_table(expenses, ["Date", "Category", "Description", "Amount"]),
        )
    )
