from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ExpenseBase(SQLModel):
    operation_date: str = Field(description="Operation date in ISO format yyyy-mm-dd")
    value_date: str = Field(description="Value date in ISO format yyyy-mm-dd")
    concept: str = Field(description="Transaction concept/description")
    amount: float = Field(description="Transaction amount; negative=expense, positive=income")
    balance: float = Field(description="Account balance after the transaction")
    category: Optional[str] = Field(default=None, index=True)
    subcategory: Optional[str] = Field(default=None)
    bank_name: Optional[str] = Field(default=None, index=True)
    is_categorized: bool = Field(default=False, index=True)


class Expense(ExpenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dedupe_hash: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    file_source: Optional[str] = Field(default=None)


class ExpenseCreate(ExpenseBase):
    dedupe_hash: str
    file_source: Optional[str] = None


class ExpenseRead(ExpenseBase):
    id: int
    dedupe_hash: str
    created_at: datetime
    file_source: Optional[str] = None
