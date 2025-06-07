from datetime import date

import reflex as rx

from budget_app.services.income_service import add_income


class IncomeState(rx.State):
    amount: float
    source: str
    description: str
    date: date = date.today()

    def submit(self):
        add_income(self.amount, self.source, self.description, self.date)
        yield rx.redirect("/incomes")
