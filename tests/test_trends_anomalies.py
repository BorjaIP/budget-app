from types import SimpleNamespace

from dashboard.anomalies import find_unusual
from dashboard.trends import monthly_category_totals


def _e(concept, amount, date, category="Ocio"):
    return SimpleNamespace(concept=concept, amount=amount, operation_date=date, category=category)


def test_monthly_totals_are_zero_filled_and_cross_the_year():
    expenses = [_e("a", -10.0, "2025-12-03"), _e("b", -5.0, "2025-12-20"), _e("c", -7.0, "2026-02-01")]

    rows = monthly_category_totals(expenses, "Ocio", "2026-02-15", months=3)

    assert rows == [
        {"month": "dic 25", "total": 15.0},
        {"month": "ene 26", "total": 0.0},
        {"month": "feb 26", "total": 7.0},
    ]


def test_monthly_totals_filter_by_category_and_ignore_income():
    expenses = [_e("a", -10.0, "2026-02-03", "Ocio"), _e("b", -4.0, "2026-02-04", None), _e("c", 99.0, "2026-02-05")]

    assert monthly_category_totals(expenses, "Todas", "2026-02-15", 1)[0]["total"] == 14.0
    assert monthly_category_totals(expenses, "Sin categorizar", "2026-02-15", 1)[0]["total"] == 4.0
    assert monthly_category_totals([], "Ocio", None) == []


def test_charge_far_above_the_category_norm_is_flagged():
    history = [_e(f"Cine {i}", -12.0, f"2026-0{1 + i % 3}-1{i}") for i in range(6)]
    big = _e("Concierto", -180.0, "2026-04-10")

    rows = find_unusual([*history, big], "2026-04-12")

    assert [r.concept for r in rows] == ["Concierto"]
    assert rows[0].reason == "15,0× lo habitual en Ocio"
    assert rows[0].amount_fmt == "180,00 €"


def test_duplicates_are_flagged_and_old_or_small_charges_are_not():
    history = [_e(f"Cine {i}", -12.0, f"2026-01-1{i}") for i in range(6)]
    twice = [_e("Taller Pepe", -90.0, "2026-04-09", "Coche"), _e("Taller Pepe", -90.0, "2026-04-09", "Coche")]
    old_big = _e("Viaje", -900.0, "2026-01-02")
    small = _e("Café", -30.0, "2026-04-10")

    rows = find_unusual([*history, *twice, old_big, small], "2026-04-12")

    assert [(r.concept, r.reason) for r in rows] == [("Taller Pepe", "Posible duplicado")]
