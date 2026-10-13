"""Monthly budget progress per category."""

import pydantic


class BudgetRow(pydantic.BaseModel):
    category: str = ""
    limit_text: str = ""
    has_limit: bool = False
    spent: float = 0.0
    spent_fmt: str = ""
    limit_fmt: str = ""
    remaining_fmt: str = ""
    percent_fmt: str = ""
    bar: str = "0%"
    over: bool = False


def _money(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_limit(text: str) -> float | None:
    """'1.200,50' or '300' -> float; blank or invalid -> None."""
    cleaned = text.strip().replace("€", "").replace(" ", "")
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def build_rows(
    categories: list[str], budgets: dict[str, float], spending: dict[str, float]
) -> list[BudgetRow]:
    """Rows with a limit first (most used first), then the rest by spending."""
    rows = []
    for category in categories:
        spent = spending.get(category, 0.0)
        limit = budgets.get(category)
        row = BudgetRow(category=category, spent=spent, spent_fmt=_money(spent))
        if limit:
            used = spent / limit * 100
            row.has_limit = True
            row.limit_text = f"{limit:.2f}".replace(".", ",").removesuffix(",00")
            row.limit_fmt = _money(limit)
            row.over = spent > limit
            row.percent_fmt = f"{used:.0f} %"
            row.bar = f"{min(used, 100):.1f}%"
            row.remaining_fmt = (
                f"{_money(spent - limit)} por encima" if row.over else f"{_money(limit - spent)} disponibles"
            )
        rows.append(row)

    def order(row: BudgetRow):
        if row.has_limit:
            return (0, -(row.spent / (budgets[row.category] or 1)))
        return (1, -row.spent)

    return sorted(rows, key=order)
