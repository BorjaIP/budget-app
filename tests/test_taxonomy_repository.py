import pytest

from dashboard.database.models import ExpenseCreate
from dashboard.database.taxonomy_repository import TaxonomyError
from dashboard.taxonomy import DEFAULT_TAXONOMY, category_names, normalize_pair, subcategory_names


def _manager(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    return DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")


def _add(manager, concept, category, subcategory, source="manual"):
    manager.bulk_insert_with_dedupe(
        [ExpenseCreate(operation_date="2026-02-01", value_date="2026-02-01", concept=concept, amount=-9.0, balance=0.0,
                       dedupe_hash=f"h-{concept}")]
    )
    row = next(e for e in manager.get_all_expenses() if e.concept == concept)
    manager.update_category(row.id, category, subcategory, source=source)
    return row.id


def _row(manager, expense_id):
    return next(e for e in manager.get_all_expenses() if e.id == expense_id)


def test_a_new_database_starts_with_the_owner_defaults(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)

    taxonomy = manager.taxonomy.load()

    assert category_names(taxonomy) == list(DEFAULT_TAXONOMY)
    assert subcategory_names(taxonomy, "Ocio") == DEFAULT_TAXONOMY["Ocio"]


def test_add_categories_and_subcategories_with_validation(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    manager.taxonomy.add_category("  Mascotas ", "veterinario y comida")
    manager.taxonomy.add_subcategory("Mascotas", "Veterinario")

    taxonomy = manager.taxonomy.load()

    assert "Mascotas" in category_names(taxonomy)
    assert subcategory_names(taxonomy, "Mascotas") == ["Veterinario"]
    with pytest.raises(TaxonomyError, match="Ya existe"):
        manager.taxonomy.add_category("Mascotas")
    with pytest.raises(TaxonomyError, match="Ya existe|ya tiene"):
        manager.taxonomy.add_subcategory("Mascotas", "Veterinario")
    with pytest.raises(ValueError, match="vacío"):
        manager.taxonomy.add_category("   ")
    with pytest.raises(TaxonomyError, match="No existe"):
        manager.taxonomy.add_subcategory("Fantasma", "X")


def test_renaming_a_category_follows_expenses_labels_and_budgets(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    expense_id = _add(manager, "Tienda Norte 1", "Ocio", "Libros")
    manager.learn_from_correction(expense_id)
    manager.set_budget("Ocio", 60.0)

    moved = manager.taxonomy.update_category("Ocio", new_name="Tiempo libre")

    assert moved == 1
    assert _row(manager, expense_id).category == "Tiempo libre"
    assert manager.get_merchant_label("tienda norte") == {"category": "Tiempo libre", "subcategory": "Libros"}
    assert manager.get_budgets() == {"Tiempo libre": 60.0}
    assert subcategory_names(manager.taxonomy.load(), "Tiempo libre")[0] == "Libros"


def test_renaming_a_subcategory_follows_expenses(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    expense_id = _add(manager, "Tienda Norte 1", "Ocio", "Libros")

    manager.taxonomy.update_subcategory("Ocio", "Libros", new_name="Lectura")

    assert _row(manager, expense_id).subcategory == "Lectura"


def test_deleting_a_subcategory_keeps_the_parent_category(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    expense_id = _add(manager, "Tienda Norte 1", "Ocio", "Libros")
    manager.learn_from_correction(expense_id)

    moved = manager.taxonomy.delete_subcategory("Ocio", "Libros")

    row = _row(manager, expense_id)
    assert moved == 1 and (row.category, row.subcategory) == ("Ocio", None)
    assert manager.get_merchant_label("tienda norte") == {"category": "Ocio", "subcategory": None}
    assert "Libros" not in subcategory_names(manager.taxonomy.load(), "Ocio")


def test_deleting_a_category_sends_its_expenses_to_otros_and_drops_labels_and_budget(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    expense_id = _add(manager, "Tienda Norte 1", "Ocio", "Libros")
    manager.learn_from_correction(expense_id)
    manager.set_budget("Ocio", 60.0)

    moved = manager.taxonomy.delete_category("Ocio")

    row = _row(manager, expense_id)
    assert moved == 1 and (row.category, row.subcategory) == ("Otros", "General")
    assert manager.get_merchant_label("tienda norte") is None
    assert manager.get_budgets() == {}
    assert "Ocio" not in category_names(manager.taxonomy.load())


def test_otros_general_is_reserved(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)

    for action in (
        lambda: manager.taxonomy.delete_category("Otros"),
        lambda: manager.taxonomy.update_category("Otros", new_name="Varios"),
        lambda: manager.taxonomy.delete_subcategory("Otros", "General"),
        lambda: manager.taxonomy.update_subcategory("Otros", "General", new_name="Nada"),
    ):
        with pytest.raises(TaxonomyError, match="reserva"):
            action()


def test_reset_restores_defaults_and_rescues_orphan_expenses(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    manager.taxonomy.add_category("Mascotas")
    expense_id = _add(manager, "Veterinario 1", "Mascotas", None)
    manager.taxonomy.delete_subcategory("Ocio", "Libros")

    moved = manager.taxonomy.reset_to_defaults()

    taxonomy = manager.taxonomy.load()
    assert moved == 1 and (_row(manager, expense_id).category, _row(manager, expense_id).subcategory) == ("Otros", "General")
    assert category_names(taxonomy) == list(DEFAULT_TAXONOMY)
    assert "Libros" in subcategory_names(taxonomy, "Ocio")


def test_normalize_pair_applies_the_parent_and_otros_rules(tmp_path, monkeypatch):
    taxonomy = _manager(tmp_path, monkeypatch).taxonomy.load()

    assert normalize_pair(taxonomy, "Ocio", "Libros") == ("Ocio", "Libros")
    assert normalize_pair(taxonomy, "Ocio", "Inexistente") == ("Ocio", None)
    assert normalize_pair(taxonomy, "Inexistente", "Libros") == ("Otros", "General")
