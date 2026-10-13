from dashboard.budgets import build_rows, parse_limit


def test_parse_limit_accepts_spanish_and_plain_numbers():
    assert parse_limit("1.200,50") == 1200.5
    assert parse_limit("300") == 300.0
    assert parse_limit(" 45,5 € ") == 45.5


def test_parse_limit_rejects_blank_invalid_and_non_positive():
    assert parse_limit("") is None
    assert parse_limit("abc") is None
    assert parse_limit("0") is None
    assert parse_limit("-5") is None


def test_rows_show_progress_and_flag_overspending():
    rows = build_rows(["Ocio", "Vivienda", "Salud"], {"Ocio": 100.0, "Vivienda": 800.0}, {"Ocio": 125.0, "Vivienda": 400.0, "Salud": 30.0})

    assert [r.category for r in rows] == ["Ocio", "Vivienda", "Salud"]
    ocio = rows[0]
    assert ocio.over is True
    assert ocio.bar == "100.0%"
    assert ocio.percent_fmt == "125 %"
    assert ocio.remaining_fmt == "25,00 € por encima"
    assert rows[1].over is False and rows[1].remaining_fmt == "400,00 € disponibles"
    assert rows[2].has_limit is False and rows[2].spent_fmt == "30,00 €"


def test_budget_storage_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    manager = DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")
    manager.set_budget("Ocio", 100.0)
    manager.set_budget("Ocio", 150.0)
    manager.set_budget("Salud", 40.0)
    manager.set_budget("Salud", None)

    assert manager.get_budgets() == {"Ocio": 150.0}
