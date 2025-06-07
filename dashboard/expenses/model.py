from typing import Optional

import reflex as rx


class Item(rx.Base):
    """The item class."""

    operation_date: str
    value_date: str
    concept: str
    amount: str
    salary: str
    category: Optional[str] = None
