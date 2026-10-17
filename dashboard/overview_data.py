"""Everything the overview shows beyond the totals, computed from plain data (no database, no UI)."""

from collections import defaultdict
from datetime import date
from typing import Any

from dashboard.overview import (
    category_segments,
    cumulative_series,
    donut_svg,
    insights,
    money,
    movers,
    pace_points,
    sankey_model,
    sankey_svg,
)
from dashboard.recurring import RecurringRow, upcoming


def _daily_spending(expenses: list, saving: set[str]) -> dict[str, float]:
    daily: dict[str, float] = defaultdict(float)
    for e in expenses:
        if e.amount < 0 and e.category not in saving:
            daily[e.operation_date] += -e.amount
    return daily


def _pace(expenses: list, saving: set[str], date_from, date_to, prev_from, prev_to, anchor) -> list[dict[str, Any]]:
    """Cumulative spending day by day against the previous period; empty when the period has no bounds."""
    if not (date_from and date_to):
        return []
    start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
    days = (end - start).days + 1
    daily = _daily_spending(expenses, saving)
    current = cumulative_series(daily, date_from, days, until=min(date_to, anchor) if anchor else date_to)
    previous = cumulative_series(daily, prev_from, days, until=prev_to) if prev_from and prev_to else None
    return pace_points(current, previous)


def build_overview(
    *,
    expenses: list,
    saving: set[str],
    date_from: str | None,
    date_to: str | None,
    prev_from: str | None,
    prev_to: str | None,
    anchor: str | None,
    breakdown: list[dict[str, Any]],
    previous_breakdown: list[dict[str, Any]],
    income_breakdown: list[dict[str, Any]],
    saved: float,
    spending_total: float,
    previous_spending: float | None,
    savings_rate: float | None,
    recurring: list[RecurringRow],
    colors: dict[str, str],
) -> dict[str, Any]:
    """The donut, cash-flow diagram, pace line, movers, sentences and upcoming charges of the overview."""
    segments = category_segments(breakdown, colors)
    changes = movers(breakdown, previous_breakdown) if previous_breakdown else []
    pending, pending_total = upcoming(recurring)
    classified = [row for row in breakdown if row["name"] != "Sin categorizar"]
    top = (classified[0]["name"], classified[0]["value"]) if classified else None
    return {
        "segments": segments,
        "donut_svg": donut_svg(segments, money(spending_total), "Gastos") if segments else "",
        "sankey_svg": sankey_svg(sankey_model(income_breakdown, breakdown, saved, colors)),
        "pace": _pace(expenses, saving, date_from, date_to, prev_from, prev_to, anchor),
        "movers": changes,
        "insights": insights(
            spending_total, previous_spending, top, changes[0] if changes else None, savings_rate, pending_total
        ),
        "upcoming": pending,
        "upcoming_total": pending_total,
    }
