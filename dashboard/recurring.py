"""Detect recurring charges (subscriptions, bills) from the expense history."""

import re
from datetime import date
from collections import defaultdict
from statistics import median
from typing import Iterable

import pydantic

MIN_MONTHS = 3
AMOUNT_TOLERANCE = 0.10
MONTHLY_GAP_DAYS = (26, 35)
MAX_IDLE_DAYS = 70


class RecurringRow(pydantic.BaseModel):
    concept: str = ""
    amount: float = 0.0
    amount_fmt: str = ""
    months: int = 0
    last_date: str = ""
    last_date_fmt: str = ""


def _money(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def normalize_concept(concept: str) -> str:
    """Lowercase and drop digits and punctuation so 'Recibo 0425 Luz' and 'Recibo 0525 Luz' match."""
    text = re.sub(r"[^a-záéíóúüñ ]+", " ", concept.lower())
    return re.sub(r"\s+", " ", text).strip()


def _days(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _is_monthly(dates: list[str]) -> bool:
    """The typical gap between consecutive charges is about one month."""
    gaps = [_days(a, b) for a, b in zip(dates, dates[1:]) if a != b]
    return bool(gaps) and MONTHLY_GAP_DAYS[0] <= median(gaps) <= MONTHLY_GAP_DAYS[1]


def find_recurring(expenses: Iterable) -> list[RecurringRow]:
    """Charges billed about once a month, at least MIN_MONTHS times, with a steady amount and still active.

    Expects objects with `concept`, `amount` and `operation_date` (yyyy-mm-dd).
    Most expensive first.
    """
    groups: dict[str, list] = defaultdict(list)
    for expense in expenses:
        if expense.amount < 0:
            key = normalize_concept(expense.concept)
            if key:
                groups[key].append(expense)

    latest = max((e.operation_date for items in groups.values() for e in items), default=None)
    rows = []
    for items in groups.values():
        amounts = [abs(e.amount) for e in items]
        typical = median(amounts)
        steady = [e for e in items if abs(abs(e.amount) - typical) <= typical * AMOUNT_TOLERANCE]
        months = {e.operation_date[:7] for e in steady}
        if len(months) < MIN_MONTHS or len(steady) > len(months) * 1.2:
            continue
        newest = max(steady, key=lambda e: e.operation_date)
        if not _is_monthly(sorted(e.operation_date for e in steady)) or _days(newest.operation_date, latest) > MAX_IDLE_DAYS:
            continue
        rows.append(
            RecurringRow(
                concept=newest.concept[:60],
                amount=round(typical, 2),
                amount_fmt=_money(typical),
                months=len(months),
                last_date=newest.operation_date,
                last_date_fmt=date.fromisoformat(newest.operation_date).strftime("%d/%m/%Y"),
            )
        )
    return sorted(rows, key=lambda r: r.amount, reverse=True)
