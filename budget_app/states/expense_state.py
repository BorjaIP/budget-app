from datetime import date

import reflex as rx

from budget_app.services.expense_service import add_expense


class ExpenseState(rx.State):
    amount: float
    category: str
    description: str
    date: date = date.today()

    def submit(self):
        add_expense(self.amount, self.category, self.description, self.date)
        yield rx.redirect("/expenses")
