import pytest

from dashboard.database.models import ExpenseCreate


def _manager(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    return DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")


def _add(manager, concept, amount=-10.0, day=1):
    manager.bulk_insert_with_dedupe(
        [ExpenseCreate(operation_date=f"2026-03-{day:02d}", value_date=f"2026-03-{day:02d}", concept=concept, amount=amount,
                       balance=0.0, dedupe_hash=f"h-{concept}")]
    )
    return next(e for e in manager.get_all_expenses() if e.concept == concept)


def _row(manager, expense_id):
    return next(e for e in manager.get_all_expenses() if e.id == expense_id)


def test_a_rule_created_by_hand_is_listed_and_applied_to_the_merchant_but_not_to_hand_made_rows(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    first = _add(manager, "Pago Movil En Tienda Norte 1", day=1)
    second = _add(manager, "Compra Tienda Norte 2", day=2)
    mine = _add(manager, "Tienda Norte 3", day=3)
    other = _add(manager, "Cafe Sur 4", day=4)
    manager.update_category(mine.id, "Ocio", "Libros", source="manual")

    key, changed = manager.save_rule("Tienda Norte", "Gastos diarios", "Comida")

    assert key == "tienda norte" and changed == 2
    assert (_row(manager, first.id).category, _row(manager, first.id).category_source) == ("Gastos diarios", "memory")
    assert _row(manager, second.id).subcategory == "Comida"
    assert _row(manager, mine.id).category == "Ocio"  # hand-made rows are never overwritten
    assert _row(manager, other.id).category is None
    assert manager.list_rules()[0]["category"] == "Gastos diarios"


def test_changing_a_rule_moves_its_movements_and_a_rule_never_applies_to_the_wrong_kind(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    spending = _add(manager, "Bizum Marta 1", amount=-20.0, day=1)
    incoming = _add(manager, "Bizum Marta 2", amount=30.0, day=2)

    manager.save_rule("Bizum Marta", "Ocio", "Libros")
    assert _row(manager, spending.id).category == "Ocio" and _row(manager, incoming.id).category is None

    manager.save_rule("Bizum Marta", "Nómina", None)  # an income category only fits the incoming one
    assert _row(manager, incoming.id).category == "Nómina" and _row(manager, spending.id).category == "Ocio"
    assert len(manager.list_rules()) == 1


def test_an_invalid_rule_is_refused_and_an_unknown_category_falls_back_to_otros(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="comercio"):
        manager.save_rule("1234", "Ocio", None)
    key, _ = manager.save_rule("Algo Raro SL", "Inventada", "x")

    assert (manager.get_merchant_label(key)["category"], manager.get_merchant_label(key)["subcategory"]) == ("Otros", "General")


def test_forgetting_a_rule_sends_its_movements_back_to_review_and_keeps_hand_made_ones(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    auto = _add(manager, "Tienda Norte 1", day=1)
    mine = _add(manager, "Tienda Norte 2", day=2)
    manager.update_category(mine.id, "Ocio", "Libros", source="manual")
    manager.save_rule("Tienda Norte", "Gastos diarios", "Comida")

    reopened = manager.delete_rule("tienda norte")

    assert reopened == 1 and manager.list_rules() == []
    assert (_row(manager, auto.id).category_source, _row(manager, auto.id).category_confidence) == ("llm", 0.0)
    assert manager.count_to_review() == 1  # the movement it had categorized is asked about again
    assert _row(manager, mine.id).category == "Ocio" and _row(manager, mine.id).category_source == "manual"
    assert manager.delete_rule("no-existe") == 0
