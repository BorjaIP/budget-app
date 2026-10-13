"""Monthly spending of one category (or all of them) over the latest months."""

from collections import defaultdict
from datetime import date
from typing import Iterable

_MONTH_ABBR = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
ALL = "Todas"
UNCATEGORIZED = "Sin categorizar"


def monthly_category_totals(
    expenses: Iterable, category: str, latest: str | None, months: int = 12
) -> list[dict]:
    """Spending per month for the `months` months ending at `latest`, zero-filled.

    `category` is a category name, "Sin categorizar" or "Todas".
    """
    if not latest:
        return []
    end = date.fromisoformat(latest)
    window = []
    index = end.year * 12 + end.month - 1
    for offset in range(months - 1, -1, -1):
        year, month = divmod(index - offset, 12)
        window.append(f"{year}-{month + 1:02d}")

    totals: dict[str, float] = defaultdict(float)
    for expense in expenses:
        if expense.amount >= 0:
            continue
        name = expense.category or UNCATEGORIZED
        if category != ALL and name != category:
            continue
        totals[expense.operation_date[:7]] += -expense.amount

    return [
        {
            "month": f"{_MONTH_ABBR[int(key[5:]) - 1]} {key[2:4]}",
            "total": round(totals.get(key, 0.0), 2),
        }
        for key in window
    ]
