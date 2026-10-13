from dashboard.database.models import ExpenseCreate


def _manager(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    return DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")


def _setup(manager):
    rows = [
        ("Nomina", 1000.0, "Nómina", None),
        ("Cine", -40.0, "Ocio", "Cine o teatro"),
        ("Traspaso a hucha", -300.0, "Ahorro", "Traspaso a cuenta de ahorro"),
        ("Retirada de hucha", 50.0, "Ahorro", "Retirada de ahorro"),
        ("Sin categoria", -10.0, None, None),
    ]
    manager.bulk_insert_with_dedupe(
        [
            ExpenseCreate(operation_date=f"2026-03-0{i + 1}", value_date=f"2026-03-0{i + 1}", concept=c, amount=a,
                          balance=0.0, dedupe_hash=f"h{i}")
            for i, (c, a, _, _) in enumerate(rows)
        ]
    )
    by_concept = {e.concept: e for e in manager.get_all_expenses()}
    for concept, _, category, sub in rows:
        if category:
            manager.update_category(by_concept[concept].id, category, sub, source="manual")


def test_transfers_to_savings_are_neither_income_nor_spending_in_any_total(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    _setup(manager)

    assert manager.saving_category_names() == {"Ahorro"}
    assert manager.get_flow_totals() == {"income": 1000.0, "spending": 50.0}
    assert {row["name"] for row in manager.get_category_breakdown()} == {"Ocio", "Sin categorizar"}
    assert "Traspaso a hucha" not in {row["concept"] for row in manager.get_top_concepts()}
    summary = manager.get_yearly_summary()[0]
    assert (summary["income"], summary["spending"], summary["savings"]) == (1000.0, 50.0, 950.0)


def test_the_net_amount_moved_to_savings_is_reported_apart(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    _setup(manager)

    assert manager.get_saving_transfers() == 250.0  # 300 out, 50 back
    assert manager.get_saving_transfers("2026-03-04", "2026-03-04") == -50.0
    assert len(manager.get_all_expenses()) == 5
    assert {e.concept for e in manager.get_all_expenses(exclude_saving=True)} == {"Nomina", "Cine", "Sin categoria"}


def test_without_a_saving_category_nothing_is_excluded(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    _setup(manager)
    manager.taxonomy.delete_category("Ahorro")

    assert manager.get_saving_transfers() == 0.0
    # the transfers moved to Otros / General, so they count again: 40 + 300 + 10 out, 1000 + 50 in
    assert manager.get_flow_totals() == {"income": 1050.0, "spending": 350.0}
