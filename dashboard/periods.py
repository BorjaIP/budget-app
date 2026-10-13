"""Period presets for the overview, anchored on the newest date in the data.

Anchoring on the data (not on today) keeps the presets useful when the last
bank export is a few weeks old.
"""

from dataclasses import dataclass
from datetime import date

PRESETS = {
    "month": "Mes",
    "3m": "3 meses",
    "12m": "12 meses",
    "year": "Año",
    "all": "Todo",
}
DEFAULT_PRESET = "12m"


@dataclass(frozen=True)
class Period:
    date_from: str | None
    date_to: str | None
    prev_from: str | None
    prev_to: str | None
    daily: bool


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def _month_end(year: int, month: int) -> date:
    ny, nm = _shift_month(year, month, 1)
    return date.fromordinal(_month_start(ny, nm).toordinal() - 1)


def _months(anchor: date, count: int, back: int = 0) -> tuple[str, str]:
    """`count` whole months ending `back` blocks before the anchor month."""
    end_y, end_m = _shift_month(anchor.year, anchor.month, -count * back)
    start_y, start_m = _shift_month(end_y, end_m, -(count - 1))
    return (
        _month_start(start_y, start_m).isoformat(),
        _month_end(end_y, end_m).isoformat(),
    )


def resolve_period(preset: str, latest: str | None) -> Period:
    """Date range (and the one right before it) for a preset or a 4-digit year."""
    if preset == "all" or not latest:
        return Period(None, None, None, None, daily=False)
    anchor = date.fromisoformat(latest)

    if preset.isdigit() and len(preset) == 4:
        year = int(preset)
        return Period(f"{year}-01-01", f"{year}-12-31", f"{year - 1}-01-01", f"{year - 1}-12-31", False)
    if preset == "year":
        return resolve_period(str(anchor.year), latest)

    count = {"month": 1, "3m": 3, "12m": 12}.get(preset, 12)
    date_from, date_to = _months(anchor, count)
    prev_from, prev_to = _months(anchor, count, back=1)
    return Period(date_from, date_to, prev_from, prev_to, daily=count == 1)


def delta_percent(current: float, previous: float) -> float | None:
    """Relative change versus the previous period; None when it cannot be computed."""
    if previous <= 0:
        return None
    return (current - previous) / previous * 100
