from types import SimpleNamespace

from dashboard.recurring import find_recurring, normalize_concept


def _e(concept: str, amount: float, date: str):
    return SimpleNamespace(concept=concept, amount=amount, operation_date=date)


def test_normalize_concept_ignores_digits_and_punctuation():
    assert normalize_concept("Recibo 0425 Luz-Norte") == normalize_concept("RECIBO 0525 luz norte")


def test_monthly_charge_with_steady_amount_is_recurring():
    expenses = [
        _e("Suscripción música 0125", -10.99, "2026-01-09"),
        _e("Suscripción música 0225", -10.99, "2026-02-09"),
        _e("Suscripción música 0325", -11.49, "2026-03-09"),
    ]

    rows = find_recurring(expenses)

    assert len(rows) == 1
    assert rows[0].months == 3
    assert rows[0].amount_fmt == "10,99 €"
    assert rows[0].last_date == "2026-03-09"


def test_two_months_or_wildly_varying_amounts_are_not_recurring():
    expenses = [
        _e("Gimnasio", -30.0, "2026-01-02"),
        _e("Gimnasio", -30.0, "2026-02-02"),
        _e("Supermercado", -20.0, "2026-01-03"),
        _e("Supermercado", -95.0, "2026-02-03"),
        _e("Supermercado", -5.0, "2026-03-03"),
    ]

    assert find_recurring(expenses) == []


def test_income_is_ignored_and_same_month_repeats_count_once():
    expenses = [
        _e("Nómina", 1500.0, "2026-01-28"),
        _e("Nómina", 1500.0, "2026-02-28"),
        _e("Nómina", 1500.0, "2026-03-28"),
        _e("Cafetería", -3.0, "2026-01-05"),
        _e("Cafetería", -3.0, "2026-01-06"),
        _e("Cafetería", -3.0, "2026-01-07"),
    ]

    assert find_recurring(expenses) == []


def test_frequent_shopping_and_discontinued_charges_are_not_recurring():
    shop = [_e("Panadería", -4.0, f"2026-0{m}-{d:02d}") for m in (1, 2, 3) for d in (3, 12, 21)]
    old = [_e("Curso antiguo", -50.0, f"2025-0{m}-10") for m in (1, 2, 3)]
    today = [_e("Alquiler", -700.0, f"2026-0{m}-01") for m in (1, 2, 3)]

    rows = find_recurring(shop + old + today)

    assert [r.concept for r in rows] == ["Alquiler"]
