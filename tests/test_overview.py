import re

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
    signed_money,
)


def test_money_formats_spanish_euros_and_drops_decimals_when_large():
    assert money(12.5) == "12,50 €"
    assert money(1234.56) == "1.235 €"
    assert signed_money(-30.0) == "−30,00 €" and signed_money(4.0) == "+4,00 €"


def test_segments_keep_the_largest_and_merge_the_rest_into_otras():
    breakdown = [{"name": f"C{i}", "value": float(100 - i * 10)} for i in range(9)]

    segments = category_segments(breakdown, {"C0": "blue"}, limit=3)

    assert [s["name"] for s in segments] == ["C0", "C1", "C2", "Otras"]
    assert segments[0]["fill"] == "var(--blue-9)" and segments[-1]["fill"] == "var(--gray-9)"
    assert round(sum(s["percent"] for s in segments)) == 100


def test_the_donut_escapes_names_and_draws_one_arc_per_segment():
    segments = category_segments([{"name": "<script>x</script>", "value": 10.0}, {"name": "B", "value": 30.0}], {})

    svg = donut_svg(segments, "40 €", "Gastos")

    assert "<script>" not in svg and "&lt;script&gt;" in svg
    assert svg.count("stroke-dasharray") == 2
    assert "40 €" in svg


def test_cumulative_series_runs_up_and_stops_after_the_last_known_day():
    daily = {"2026-03-01": 10.0, "2026-03-03": 5.0}

    assert cumulative_series(daily, "2026-03-01", 5) == [10.0, 10.0, 15.0, 15.0, 15.0]
    assert cumulative_series(daily, "2026-03-01", 5, until="2026-03-03") == [10.0, 10.0, 15.0, None, None]


def test_pace_points_pair_both_periods_by_day_and_thin_long_ones():
    rows = pace_points([1.0, 2.0, 3.0], [1.0, 1.0])

    assert rows == [
        {"day": 1, "actual": 1.0, "anterior": 1.0},
        {"day": 2, "actual": 2.0, "anterior": 1.0},
        {"day": 3, "actual": 3.0, "anterior": None},
    ]
    long = pace_points([float(i) for i in range(365)], None, max_points=45)
    assert len(long) <= 47 and long[-1]["day"] == 365


def test_movers_rank_by_the_size_of_the_change_with_a_bar_relative_to_the_largest():
    current = [{"name": "Ocio", "value": 150.0}, {"name": "Comida", "value": 100.0}, {"name": "Nuevo", "value": 20.0}]
    previous = [{"name": "Ocio", "value": 50.0}, {"name": "Comida", "value": 160.0}, {"name": "Viejo", "value": 5.0}]

    rows = movers(current, previous, limit=3)

    assert [r["name"] for r in rows] == ["Ocio", "Comida", "Nuevo"]
    assert rows[0]["up"] and rows[0]["delta_fmt"] == "+100,00 €" and rows[0]["bar"] == "100%"
    assert not rows[1]["up"] and rows[1]["delta_fmt"] == "−60,00 €"


def test_insights_are_plain_sentences_and_skip_what_is_missing():
    lines = insights(
        spending=1000.0,
        previous_spending=1250.0,
        top_category=("Vivienda", 450.0),
        mover={"name": "Ocio", "up": True, "delta_fmt": "+80,00 €"},
        savings_rate=18.4,
        upcoming_total=210.0,
    )

    assert lines[0] == "Has gastado 1.000 €, un 20 % menos que en el periodo anterior."
    assert "Vivienda es lo que más pesa: el 45 % de tus gastos." in lines
    assert any("Lo que más sube" in line and "Ocio" in line for line in lines)
    assert insights(0.0, None, None, None, None, None) == []


def test_sankey_balances_with_a_surplus_or_a_shortfall():
    surplus = sankey_model([{"name": "Nómina", "value": 2000.0}], [{"name": "Vivienda", "value": 800.0}], 300.0, {})
    shortfall = sankey_model([{"name": "Nómina", "value": 500.0}], [{"name": "Vivienda", "value": 800.0}], 0.0, {})

    assert [u["name"] for u in surplus["uses"]] == ["Vivienda", "Ahorro", "Sobrante"]
    assert surplus["uses"][-1]["value"] == 900.0 and surplus["total"] == 2000.0
    assert [s["name"] for s in shortfall["sources"]] == ["Nómina", "Saldo previo"]
    assert sum(s["value"] for s in shortfall["sources"]) == sum(u["value"] for u in shortfall["uses"])
    assert sankey_model([], [], 0.0, {}) is None


def test_money_coming_back_from_savings_is_a_source():
    model = sankey_model([{"name": "Nómina", "value": 1000.0}], [{"name": "Vivienda", "value": 1100.0}], -200.0, {})

    assert [s["name"] for s in model["sources"]] == ["Nómina", "Desde ahorro"]
    assert model["uses"][-1]["name"] == "Sobrante" and model["uses"][-1]["value"] == 100.0


def test_sankey_svg_is_valid_finite_and_escapes_names():
    model = sankey_model(
        [{"name": "Nómina", "value": 2100.0}],
        [{"name": f"Cat <{i}>", "value": float(50 + i * 40)} for i in range(10)],
        150.0,
        {"Nómina": "jade"},
    )

    svg = sankey_svg(model)

    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "<Cat" not in svg and "&lt;" in svg
    assert "nan" not in svg.lower() and "inf" not in svg.lower()
    assert "Otras" in svg  # more than seven spending categories are merged
    assert len(re.findall(r"<path ", svg)) == len(model["sources"]) + len(model["uses"])
    assert sankey_svg(None) == ""


def test_build_overview_assembles_every_piece_from_plain_data():
    from types import SimpleNamespace

    from dashboard.overview_data import build_overview

    def row(day, amount, category):
        return SimpleNamespace(operation_date=f"2026-04-{day:02d}", amount=amount, category=category)

    expenses = [row(2, -30.0, "Ocio"), row(5, -70.0, "Vivienda"), row(6, -300.0, "Ahorro"), row(8, 2000.0, "Nómina")]
    previous = [{"name": "Ocio", "value": 10.0}, {"name": "Vivienda", "value": 70.0}]

    overview = build_overview(
        expenses=expenses, saving={"Ahorro"}, date_from="2026-04-01", date_to="2026-04-30",
        prev_from="2026-03-01", prev_to="2026-03-31", anchor="2026-04-10",
        breakdown=[{"name": "Vivienda", "value": 70.0}, {"name": "Ocio", "value": 30.0}],
        previous_breakdown=previous, income_breakdown=[{"name": "Nómina", "value": 2000.0}], saved=300.0,
        spending_total=100.0, previous_spending=80.0, savings_rate=95.0, recurring=[], colors={"Ocio": "purple"},
    )

    assert [s["name"] for s in overview["segments"]] == ["Vivienda", "Ocio"]
    assert overview["donut_svg"].startswith("<svg") and overview["sankey_svg"].startswith("<svg")
    pace = overview["pace"]
    assert len(pace) == 30 or len(pace) <= 47
    assert pace[0]["day"] == 1 and pace[1]["actual"] == 30.0  # transfers to savings never count as spending
    assert next(p for p in pace if p["day"] == 10)["actual"] == 100.0 and next(p for p in pace if p["day"] == 12)["actual"] is None
    assert overview["movers"][0]["name"] == "Ocio" and overview["movers"][0]["up"]
    assert overview["insights"][0] == "Has gastado 100,00 €, un 25 % más que en el periodo anterior."


def test_without_period_bounds_there_is_no_pace_and_without_data_no_pictures():
    from dashboard.overview_data import build_overview

    overview = build_overview(
        expenses=[], saving=set(), date_from=None, date_to=None, prev_from=None, prev_to=None, anchor=None,
        breakdown=[], previous_breakdown=[], income_breakdown=[], saved=0.0, spending_total=0.0,
        previous_spending=None, savings_rate=None, recurring=[], colors={},
    )

    assert overview["pace"] == [] and overview["donut_svg"] == "" and overview["sankey_svg"] == ""
    assert overview["insights"] == [] and overview["upcoming"] == []


def test_uncategorized_is_never_reported_as_a_mover():
    rows = movers([{"name": "Sin categorizar", "value": 500.0}, {"name": "Ocio", "value": 60.0}], [{"name": "Ocio", "value": 10.0}])

    assert [r["name"] for r in rows] == ["Ocio"]


def test_the_cash_flow_picture_grows_with_the_number_of_labels():
    few = sankey_svg(sankey_model([{"name": "Nómina", "value": 100.0}], [{"name": "A", "value": 50.0}], 0.0, {}))
    many = sankey_svg(sankey_model([{"name": "Nómina", "value": 3000.0}], [{"name": f"C{i}", "value": 100.0 + i} for i in range(7)], 200.0, {}))

    assert re.search(r'viewBox="0 0 760 (\d+)"', many) and int(re.search(r'viewBox="0 0 760 (\d+)"', many).group(1)) > int(re.search(r'viewBox="0 0 760 (\d+)"', few).group(1))
