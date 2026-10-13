from dashboard.database.models import ExpenseCreate


def _expense(index: int) -> ExpenseCreate:
    return ExpenseCreate(
        operation_date="2026-01-1%d" % index,
        value_date="2026-01-1%d" % index,
        concept=f"Compra de prueba {index}",
        amount=-12.5,
        balance=100.0,
        dedupe_hash=f"hash-{index}",
    )


def test_bulk_insert_stores_and_reads_back_expenses(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    manager = DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")

    result = manager.bulk_insert_with_dedupe([_expense(1), _expense(2)])

    assert result == {"inserted": 2, "skipped": 0}
    assert len(manager.get_recent_expenses(limit=5)) == 2


def test_bulk_insert_skips_duplicates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    manager = DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")
    manager.bulk_insert_with_dedupe([_expense(1)])

    result = manager.bulk_insert_with_dedupe([_expense(1)])

    assert result == {"inserted": 0, "skipped": 1}
