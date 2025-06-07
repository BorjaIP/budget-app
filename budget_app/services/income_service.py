from budget_app.database.db import SessionLocal
from budget_app.models.income import Income


def add_income(amount, source, description, date):
    db = SessionLocal()
    db.add(Income(amount=amount, source=source, description=description, date=date))
    db.commit()
    db.close()


def get_all_incomes():
    db = SessionLocal()
    incomes = db.query(Income).all()
    db.close()
    return incomes
