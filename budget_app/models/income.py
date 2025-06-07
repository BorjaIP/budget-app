from datetime import date
from .base import Base

class Income(Base, table=True):
    amount: float
    source: str
    description: str
    date: date
