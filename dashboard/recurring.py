"""Detect recurring charges (subscriptions, bills) and estimate what is still to be paid this month."""

import re
from collections import defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Iterable

import pydantic

MIN_MONTHS = 3
AMOUNT_TOLERANCE = 0.10
VARIABLE_TOLERANCE = 0.60  # electricity, gas, water: the bill changes but it always comes
VARIABLE_MIN_MONTHS = 4
RECENT = 6  # charges the estimate looks at
MONTHLY_GAP_DAYS = (26, 35)
MAX_IDLE_DAYS = 70


class RecurringRow(pydantic.BaseModel):
    concept: str = ""
    amount: float = 0.0
    amount_fmt: str = ""
    months: int = 0
    last_date: str = ""
    last_date_fmt: str = ""
    variable: bool = False
    estimate: float = 0.0
    estimate_fmt: str = ""
    range_fmt: str = ""
    next_date: str = ""
    next_date_fmt: str = ""
    pending: bool = False  # still to be charged this month


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


def _next_month(day: date) -> date:
    year, month = (day.year + 1, 1) if day.month == 12 else (day.year, day.month + 1)
    last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(day.day, last))


def _month_end(day: date) -> date:
    return (date(day.year + (day.month == 12), day.month % 12 + 1, 1)) - timedelta(days=1)


def _same_day_each_month(dates: list[str], spread: int = 7) -> bool:
    """Bills arrive on about the same day every month; a shop visited monthly does not."""
    days = [int(d[8:10]) for d in dates]
    return max(days) - min(days) <= spread


def _monthly_group(items: list, tolerance: float, min_months: int, latest: str, same_day: bool = False):
    """The charges of one concept that look like a monthly bill, or None."""
    typical = median(abs(e.amount) for e in items)
    steady = [e for e in items if abs(abs(e.amount) - typical) <= typical * tolerance]
    months = {e.operation_date[:7] for e in steady}
    if len(months) < min_months or len(steady) > len(months) * 1.2:
        return None
    steady.sort(key=lambda e: e.operation_date)
    if not _is_monthly([e.operation_date for e in steady]) or _days(steady[-1].operation_date, latest) > MAX_IDLE_DAYS:
        return None
    if same_day and not _same_day_each_month([e.operation_date for e in steady]):
        return None
    return steady, len(months)


def find_recurring(expenses: Iterable) -> list[RecurringRow]:
    """Charges billed about once a month and still active, with an estimate of the next one.

    Fixed ones keep their amount within 10 %; bills that vary (electricity, gas) need four months and are estimated
    from their last six charges. Expects objects with `concept`, `amount` and `operation_date` (yyyy-mm-dd), and
    treats the newest date as "today". Most expensive first.
    """
    groups: dict[str, list] = defaultdict(list)
    for expense in expenses:
        if expense.amount < 0:
            key = normalize_concept(expense.concept)
            if key:
                groups[key].append(expense)

    latest = max((e.operation_date for items in groups.values() for e in items), default=None)
    if latest is None:
        return []
    today = date.fromisoformat(latest)
    month_start, month_end = today.replace(day=1), _month_end(today)

    rows = []
    for items in groups.values():
        variable = False
        found = _monthly_group(items, AMOUNT_TOLERANCE, MIN_MONTHS, latest)
        if found is None:
            found = _monthly_group(items, VARIABLE_TOLERANCE, VARIABLE_MIN_MONTHS, latest, same_day=True)
            variable = found is not None
        if found is None:
            continue
        steady, months = found
        newest = steady[-1]
        recent = [abs(e.amount) for e in steady[-RECENT:]]
        estimate = median(recent)
        last = date.fromisoformat(newest.operation_date)
        following = _next_month(last)
        rows.append(
            RecurringRow(
                concept=newest.concept[:60],
                amount=round(median(abs(e.amount) for e in steady), 2),
                amount_fmt=_money(median(abs(e.amount) for e in steady)),
                months=months,
                last_date=newest.operation_date,
                last_date_fmt=last.strftime("%d/%m/%Y"),
                variable=variable,
                estimate=round(estimate, 2),
                estimate_fmt=("≈ " if variable else "") + _money(estimate),
                range_fmt=f"{_money(min(recent))} a {_money(max(recent))}" if variable else "",
                next_date=following.isoformat(),
                next_date_fmt=following.strftime("%d/%m/%Y"),
                pending=last < month_start and following <= month_end,
            )
        )
    return sorted(rows, key=lambda r: r.estimate, reverse=True)


def upcoming(rows: list[RecurringRow]) -> tuple[list[RecurringRow], float]:
    """The recurring charges still to come this month, soonest first, and what they add up to."""
    pending = sorted((r for r in rows if r.pending), key=lambda r: r.next_date)
    return pending, round(sum(r.estimate for r in pending), 2)
