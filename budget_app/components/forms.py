import reflex as rx

from budget_app.states.expense_state import ExpenseState
from budget_app.states.income_state import IncomeState


def income_form():
    return rx.form(
        rx.input("Amount", on_change=IncomeState.set_amount),
        rx.input("Source", on_change=IncomeState.set_source),
        rx.input("Description", on_change=IncomeState.set_description),
        rx.input("Date", type="date", on_change=IncomeState.set_date),
        rx.button("Add Income", on_click=IncomeState.submit),
    )


def expense_form():
    return rx.form(
        rx.input("Amount", on_change=ExpenseState.set_amount),
        rx.input("Category", on_change=ExpenseState.set_category),
        rx.input("Description", on_change=ExpenseState.set_description),
        rx.input("Date", type="date", on_change=ExpenseState.set_date),
        rx.button("Add Expense", on_click=ExpenseState.submit),
    )
