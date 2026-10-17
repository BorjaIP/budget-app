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


def test_a_bill_that_varies_every_month_is_recurring_and_estimated_from_recent_charges():
    bills = [
        _e("Recibo luz Sol", -amount, f"2026-0{month}-12")
        for month, amount in [(1, 96.0), (2, 82.0), (3, 70.0), (4, 55.0), (5, 48.0), (6, 52.0)]
    ]

    rows = find_recurring(bills)

    assert len(rows) == 1 and rows[0].variable
    assert rows[0].estimate == 62.5  # median of the six
    assert rows[0].estimate_fmt == "≈ 62,50 €" and rows[0].range_fmt == "48,00 € a 96,00 €"
    assert rows[0].next_date == "2026-07-12"


def test_fixed_charges_keep_the_plain_amount_and_a_wildly_irregular_one_is_not_recurring():
    fixed = [_e("Internet Costa", -39.0, f"2026-0{m}-05") for m in (1, 2, 3, 4)]
    chaotic = [_e("Compras raras", -a, f"2026-0{m}-15") for m, a in [(1, 10.0), (2, 200.0), (3, 5.0), (4, 90.0)]]

    rows = find_recurring(fixed + chaotic)

    assert [r.concept for r in rows] == ["Internet Costa"]
    assert not rows[0].variable and rows[0].estimate_fmt == "39,00 €" and rows[0].range_fmt == ""


def test_what_is_still_to_be_charged_this_month_is_listed_with_its_estimate():
    from dashboard.recurring import upcoming

    rent = [_e("Alquiler piso", -700.0, f"2026-0{m}-01") for m in (1, 2, 3, 4)]  # already paid on April 1st
    internet = [_e("Internet Costa", -39.0, f"2026-0{m}-20") for m in (1, 2, 3)]  # due on the 20th
    light = [_e("Recibo luz Sol", -a, d) for a, d in [(90.0, "2025-12-25"), (70.0, "2026-01-25"), (60.0, "2026-02-25"), (50.0, "2026-03-25")]]
    today = [_e("Cafe", -2.0, "2026-04-10")]  # the newest date is April 10th, so that is "today"

    pending, total = upcoming(find_recurring(rent + internet + light + today))

    assert [(r.concept, r.next_date) for r in pending] == [("Internet Costa", "2026-04-20"), ("Recibo luz Sol", "2026-04-25")]
    assert total == 39.0 + 65.0  # the light estimate is the median of its four charges


def test_a_shop_visited_monthly_on_different_days_is_not_a_variable_bill():
    visits = [_e("Farmacia Central", -a, f"2026-0{m}-{d:02d}") for m, a, d in [(1, 12.0, 3), (2, 30.0, 21), (3, 18.0, 9), (4, 25.0, 28), (5, 9.0, 14)]]

    assert find_recurring(visits) == []
