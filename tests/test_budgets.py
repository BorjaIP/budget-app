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


def test_categorization_snapshot_restores_what_a_reset_changed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.models import ExpenseCreate
    from dashboard.database.operations import DatabaseManager

    manager = DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")
    manager.bulk_insert_with_dedupe(
        [
            ExpenseCreate(operation_date="2026-01-01", value_date="2026-01-01", concept="A", amount=-1.0, balance=0.0, dedupe_hash="a"),
            ExpenseCreate(operation_date="2026-01-02", value_date="2026-01-02", concept="B", amount=-2.0, balance=0.0, dedupe_hash="b"),
        ]
    )
    ids = [e.id for e in manager.get_all_expenses()]
    manager.update_category(ids[0], "Ocio", "Libros", source="llm")
    manager.update_category(ids[1], "Salud", None, source="manual")
    snapshot = manager.snapshot_categorization()

    manager.reset_categorization()
    manager.update_category(ids[0], "Deuda", "Otros", source="llm")
    manager.restore_categorization(snapshot)

    rows = {e.id: e for e in manager.get_all_expenses()}
    assert (rows[ids[0]].category, rows[ids[0]].subcategory, rows[ids[0]].is_categorized) == ("Ocio", "Libros", True)
    assert rows[ids[1]].category == "Salud" and rows[ids[1]].category_source == "manual"
    assert len(snapshot) == 1
