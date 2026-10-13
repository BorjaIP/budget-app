from dashboard.database.models import ExpenseCreate
from dashboard.periods import delta_percent, resolve_period


def test_month_preset_is_the_calendar_month_of_the_latest_date():
    period = resolve_period("month", "2026-03-17")

    assert (period.date_from, period.date_to) == ("2026-03-01", "2026-03-31")
    assert (period.prev_from, period.prev_to) == ("2026-02-01", "2026-02-28")
    assert period.daily is True


def test_three_months_end_at_the_latest_month_and_cross_the_year():
    period = resolve_period("3m", "2026-02-10")

    assert (period.date_from, period.date_to) == ("2025-12-01", "2026-02-28")
    assert (period.prev_from, period.prev_to) == ("2025-09-01", "2025-11-30")
    assert period.daily is False


def test_twelve_months_and_leap_february():
    period = resolve_period("12m", "2024-02-29")

    assert (period.date_from, period.date_to) == ("2023-03-01", "2024-02-29")
    assert (period.prev_from, period.prev_to) == ("2022-03-01", "2023-02-28")


def test_year_presets():
    assert resolve_period("year", "2026-03-17").date_from == "2026-01-01"
    period = resolve_period("2025", "2026-03-17")
    assert (period.date_from, period.date_to) == ("2025-01-01", "2025-12-31")
    assert (period.prev_from, period.prev_to) == ("2024-01-01", "2024-12-31")


def test_all_or_no_data_has_no_bounds():
    for period in (resolve_period("all", "2026-03-17"), resolve_period("12m", None)):
        assert (period.date_from, period.date_to, period.prev_from, period.prev_to) == (None,) * 4


def test_delta_percent():
    assert delta_percent(90.0, 100.0) == -10.0
    assert delta_percent(50.0, 0.0) is None


def _expense(index: int, amount: float, date: str, category: str | None) -> ExpenseCreate:
    return ExpenseCreate(
        operation_date=date,
        value_date=date,
        concept=f"Movimiento {index}",
        amount=amount,
        balance=0.0,
        category=category,
        dedupe_hash=f"hash-{index}",
    )


def test_flow_totals_respect_the_range_and_uncategorized_count(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    manager = DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")
    manager.bulk_insert_with_dedupe(
        [
            _expense(1, 1000.0, "2026-01-05", None),
            _expense(2, -40.0, "2026-01-10", "Ocio"),
            _expense(3, -10.5, "2026-02-01", None),
        ]
    )

    assert manager.get_flow_totals("2026-01-01", "2026-01-31") == {"income": 1000.0, "spending": 40.0}
    assert manager.get_flow_totals() == {"income": 1000.0, "spending": 50.5}
    assert manager.count_uncategorized() == 2
