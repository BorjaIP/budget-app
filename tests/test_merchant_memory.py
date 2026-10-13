import sqlite3

from dashboard.database.models import ExpenseCreate


def _expense(index: int, concept: str, amount: float = -10.0) -> ExpenseCreate:
    return ExpenseCreate(
        operation_date=f"2026-02-{index:02d}",
        value_date=f"2026-02-{index:02d}",
        concept=concept,
        amount=amount,
        balance=0.0,
        dedupe_hash=f"hash-{index}",
    )


def _manager(tmp_path):
    from dashboard.database.operations import DatabaseManager

    return DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")


def test_an_old_database_gets_the_new_columns_without_losing_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "expenses.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE expense (id INTEGER PRIMARY KEY, operation_date TEXT, value_date TEXT, concept TEXT,"
        " amount FLOAT, balance FLOAT, category TEXT, subcategory TEXT, bank_name TEXT, is_categorized BOOLEAN,"
        " dedupe_hash TEXT, created_at TIMESTAMP, file_source TEXT)"
    )
    conn.execute(
        "INSERT INTO expense (operation_date, value_date, concept, amount, balance, is_categorized, dedupe_hash)"
        " VALUES ('2026-01-01', '2026-01-01', 'Old row', -5, 0, 0, 'old')"
    )
    conn.commit()
    conn.close()

    manager = _manager(tmp_path)
    rows = manager.get_all_expenses()

    assert [r.concept for r in rows] == ["Old row"]
    assert rows[0].category_confidence is None and rows[0].category_source is None


def test_a_correction_is_remembered_and_applied_to_the_same_merchant(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = _manager(tmp_path)
    manager.bulk_insert_with_dedupe(
        [
            _expense(1, "Pago Movil En Tienda Norte, Madrid, Tarj. :*0001"),
            _expense(2, "Pago Movil En Tienda Norte, Madrid, Tarj. :*0002"),
            _expense(3, "Compra Tienda Norte, Madrid, Tarjeta 0003"),
            _expense(4, "Pago Movil En Cafe Sur, Madrid, Tarj. :*0004"),
        ]
    )
    first, second, third, other = [e.id for e in sorted(manager.get_all_expenses(), key=lambda e: e.operation_date)]
    manager.update_category(first, "Gastos diarios", "Comida", source="manual")

    changed = manager.learn_from_correction(first)

    rows = {e.id: e for e in manager.get_all_expenses()}
    assert changed == 2
    assert (rows[second].category, rows[second].category_source) == ("Gastos diarios", "memory")
    assert rows[third].category == "Gastos diarios"
    assert rows[other].category is None
    assert manager.get_merchant_label("tienda norte") == {"category": "Gastos diarios", "subcategory": "Comida"}


def test_hand_made_rows_are_never_overwritten_by_the_memory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = _manager(tmp_path)
    manager.bulk_insert_with_dedupe([_expense(1, "Tienda Norte 1"), _expense(2, "Tienda Norte 2")])
    first, second = [e.id for e in sorted(manager.get_all_expenses(), key=lambda e: e.operation_date)]
    manager.update_category(second, "Ocio", "Libros", source="manual")
    manager.update_category(first, "Gastos diarios", "Comida", source="manual")

    assert manager.learn_from_correction(first) == 0

    rows = {e.id: e for e in manager.get_all_expenses()}
    assert rows[second].category == "Ocio"


def test_the_newest_correction_wins_and_confirmations_count(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = _manager(tmp_path)
    manager.bulk_insert_with_dedupe([_expense(1, "Tienda Norte 1"), _expense(2, "Tienda Norte 2")])
    first, second = [e.id for e in sorted(manager.get_all_expenses(), key=lambda e: e.operation_date)]
    manager.update_category(first, "Gastos diarios", "Comida", source="manual")
    manager.learn_from_correction(first)
    manager.update_category(second, "Gastos diarios", "Comida", source="manual")
    manager.learn_from_correction(second)

    assert manager.get_merchant_labels()[0]["confirmations"] == 2

    manager.update_category(second, "Ocio", "Libros", source="manual")
    manager.learn_from_correction(second)

    assert manager.get_merchant_label("tienda norte") == {"category": "Ocio", "subcategory": "Libros"}
    assert manager.get_merchant_labels()[0]["confirmations"] == 1


def test_sync_backfills_labels_from_older_manual_categories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = _manager(tmp_path)
    manager.bulk_insert_with_dedupe([_expense(1, "Tienda Norte 1"), _expense(2, "Cafe Sur 2")])
    first, second = [e.id for e in sorted(manager.get_all_expenses(), key=lambda e: e.operation_date)]
    manager.update_category(first, "Gastos diarios", "Comida", source="manual")
    manager.update_category(second, "Ocio", "Libros", source="llm")

    assert manager.sync_merchant_memory() == 1
    assert manager.sync_merchant_memory() == 0
    assert [m["merchant_key"] for m in manager.get_merchant_labels()] == ["tienda norte"]


def test_review_queue_has_uncategorized_and_low_confidence_model_answers_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = _manager(tmp_path)
    manager.bulk_insert_with_dedupe([_expense(i, f"Shop {i}") for i in range(1, 6)])
    ids = [e.id for e in sorted(manager.get_all_expenses(), key=lambda e: e.operation_date)]
    manager.update_category(ids[0], "Ocio", "Libros", source="llm", confidence=0.95)
    manager.update_category(ids[1], "Ocio", "Libros", source="llm", confidence=0.2)
    manager.update_category(ids[2], "Ocio", "Libros", source="manual")
    manager.update_category(ids[3], "Ocio", "Libros", source="memory")
    # ids[4] stays without a category

    assert manager.count_to_review() == 2
    rows, total = manager.get_expenses_paginated(review_only=True)
    assert total == 2 and {r.id for r in rows} == {ids[1], ids[4]}
