from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class ExpenseBase(SQLModel):
    """Base model for expense data"""
    operation_date: str = Field(description="Date of operation")
    value_date: str = Field(description="Value date")
    concept: str = Field(description="Transaction concept/description")
    amount: str = Field(description="Transaction amount")
    salary: str = Field(description="Account balance/salary")
    category: Optional[str] = Field(default=None, description="Expense category")


class Expense(ExpenseBase, table=True):
    """Expense table model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    file_source: Optional[str] = Field(default=None, description="Source file name")


class ExpenseCreate(ExpenseBase):
    """Model for creating new expenses"""
    file_source: Optional[str] = None


class ExpenseRead(ExpenseBase):
    """Model for reading expenses"""
    id: int
    created_at: datetime
    file_source: Optional[str] = None 