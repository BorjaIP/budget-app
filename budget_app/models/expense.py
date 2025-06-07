from datetime import date
from .base import Base

class Expense(Base, table=True):
    amount: float
    category: str
    description: str
    date: date
