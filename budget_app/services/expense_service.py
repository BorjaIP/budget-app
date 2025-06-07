from budget_app.database.db import SessionLocal
from budget_app.models.expense import Expense


def add_expense(amount, category, description, date):
    db = SessionLocal()
    db.add(Expense(amount=amount, category=category, description=description, date=date))
    db.commit()
    db.close()


def get_all_expenses():
    db = SessionLocal()
    expenses = db.query(Expense).all()
    db.close()
    return expenses
