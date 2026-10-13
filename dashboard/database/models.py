from datetime import datetime
from typing import Optional

from pydantic import NaiveDatetime
from sqlalchemy import UniqueConstraint
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
    category_source: Optional[str] = Field(default=None)  # manual | memory | llm
    category_confidence: Optional[float] = Field(
        default=None, description="Model confidence in 0..1; set only for llm-assigned categories"
    )


class Expense(ExpenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dedupe_hash: str = Field(unique=True, index=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.now)
    file_source: Optional[str] = Field(default=None)


class ExpenseCreate(ExpenseBase):
    dedupe_hash: str
    file_source: Optional[str] = None


class ExpenseRead(ExpenseBase):
    id: int
    dedupe_hash: str
    created_at: datetime
    file_source: Optional[str] = None


class CategoryBudget(SQLModel, table=True):
    """Monthly spending limit for one category (names come from CATEGORY_TAXONOMY)."""

    category: str = Field(primary_key=True)
    monthly_limit: float = Field(description="Monthly limit in euros; always positive")


class MerchantLabel(SQLModel, table=True):
    """What the user taught the app: one category per merchant key (see llm/merchant.py)."""

    merchant_key: str = Field(primary_key=True)
    category: str
    subcategory: Optional[str] = None
    sample_concept: str = Field(description="One real concept of this merchant, used as a prompt example")
    confirmations: int = Field(default=1, description="Times the user confirmed this label")
    updated_at: NaiveDatetime = Field(default_factory=datetime.now)


class Category(SQLModel, table=True):
    """A category of the user's taxonomy; expenses store its name."""

    name: str = Field(primary_key=True)
    description: str = Field(default="", description="What belongs here; sent to the model")
    position: int = Field(default=0)
    kind: str = Field(default="expense", description="expense | income; the amount's sign picks the kind")


class Subcategory(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("category", "name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(index=True)
    name: str
    description: str = Field(default="")
    position: int = Field(default=0)
