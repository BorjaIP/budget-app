"""Unusual charges: far above what a category normally costs, or charged twice."""

from collections import defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Iterable

import pydantic

from dashboard.recurring import normalize_concept

WINDOW_DAYS = 45
FACTOR = 3.0
MIN_AMOUNT = 50.0
MIN_SAMPLES = 5
LIMIT = 8


class UnusualRow(pydantic.BaseModel):
    concept: str = ""
    amount_fmt: str = ""
    date_fmt: str = ""
    reason: str = ""
    sort_date: str = ""


def _money(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def find_unusual(expenses: Iterable, latest: str | None) -> list[UnusualRow]:
    """Charges of the last WINDOW_DAYS days that stand out. Newest first."""
    if not latest:
        return []
    spending = [e for e in expenses if e.amount < 0]
    since = (date.fromisoformat(latest) - timedelta(days=WINDOW_DAYS)).isoformat()

    by_category: dict[str, list[float]] = defaultdict(list)
    for e in spending:
        by_category[e.category or "Sin categorizar"].append(-e.amount)
    typical = {
        name: median(values) for name, values in by_category.items() if len(values) >= MIN_SAMPLES
    }

    rows: list[UnusualRow] = []
    seen: dict[tuple, int] = defaultdict(int)
    for e in sorted(spending, key=lambda e: e.operation_date):
        if e.operation_date < since:
            continue
        amount = -e.amount
        key = (normalize_concept(e.concept), amount, e.operation_date)
        seen[key] += 1
        name = e.category or "Sin categorizar"
        reason = None
        if seen[key] == 2:
            reason = "Posible duplicado"
        elif name in typical and amount >= max(typical[name] * FACTOR, MIN_AMOUNT):
            reason = f"{amount / typical[name]:.1f}× lo habitual en {name}".replace(".", ",")
        if reason:
            rows.append(
                UnusualRow(
                    concept=e.concept[:60],
                    amount_fmt=_money(amount),
                    date_fmt=date.fromisoformat(e.operation_date).strftime("%d/%m/%Y"),
                    reason=reason,
                    sort_date=e.operation_date,
                )
            )
    return sorted(rows, key=lambda r: r.sort_date, reverse=True)[:LIMIT]
