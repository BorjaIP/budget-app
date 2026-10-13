from typing import Optional

import pydantic


class Item(pydantic.BaseModel):
    """UI representation of an expense row."""

    id: int = 0
    operation_date: str = ""
    operation_date_human: str = ""
    value_date: str = ""
    concept: str = ""
    amount: float = 0.0
    amount_fmt: str = ""
    balance: float = 0.0
    balance_fmt: str = ""
    is_expense: bool = False
    category: Optional[str] = None
    subcategory: Optional[str] = None
    bank_name: Optional[str] = None
    is_categorized: bool = False
    concept_segments: list[dict] = []
    needs_review: bool = False
    repeat_count: int = 1
    source: Optional[str] = None
