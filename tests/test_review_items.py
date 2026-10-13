from types import SimpleNamespace

from dashboard.expenses.state import _one_per_merchant


def _row(index: int, concept: str, confidence: float):
    return SimpleNamespace(
        id=index, operation_date="2026-03-01", value_date="2026-03-01", concept=concept, amount=-5.0, balance=0.0,
        category="Otros", subcategory="General", bank_name=None, is_categorized=True, category_source="llm",
        category_confidence=confidence,
    )


def test_the_review_list_has_one_row_per_merchant_most_doubtful_first_with_its_count():
    rows = [
        _row(1, "Pago Movil En Tienda Norte, Madrid, Tarj. :*0001", 0.1),
        _row(2, "Pago Movil En Tienda Norte, Madrid, Tarj. :*0002", 0.3),
        _row(3, "Pago Movil En Cafe Sur, Madrid, Tarj. :*0003", 0.2),
    ]

    items = _one_per_merchant(rows)

    assert [(i.id, i.repeat_count) for i in items] == [(1, 2), (3, 1)]
