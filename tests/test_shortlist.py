from dashboard.llm.shortlist import shortlist
from dashboard.taxonomy import CategoryEntry


def _taxonomy(n: int, **descriptions) -> list[CategoryEntry]:
    entries = [CategoryEntry(f"Cat{i:03d}") for i in range(n)]
    entries.append(CategoryEntry("Otros"))
    return [CategoryEntry(c.name, descriptions.get(c.name, "")) for c in entries]


def _label(concept, category):
    return {"concept": concept, "category": category, "subcategory": None, "confirmations": 1}


def test_a_small_taxonomy_is_offered_whole():
    taxonomy = _taxonomy(10)

    assert shortlist(taxonomy, "x", []) is taxonomy


def test_a_long_taxonomy_is_cut_to_the_cap_and_always_keeps_otros():
    result = shortlist(_taxonomy(100), "something", [], cap=30)

    assert len(result) == 30 and "Otros" in [c.name for c in result]


def test_categories_of_similar_labels_and_the_most_used_ones_make_the_list():
    labels = [_label("Panaderia Norte 1", "Cat077"), _label("Panaderia Norte 2", "Cat077"), _label("Gimnasio Sol", "Cat042")]

    names = [c.name for c in shortlist(_taxonomy(100), "Compra Panaderia Norte", labels, cap=5)]

    assert "Cat077" in names and "Cat042" in names and "Otros" in names


def test_a_new_category_without_labels_is_found_from_its_description():
    taxonomy = _taxonomy(100, Cat050="veterinario y comida de animales")

    names = [c.name for c in shortlist(taxonomy, "Clinica veterinario Sol", [], cap=5)]

    assert "Cat050" in names


def test_the_result_keeps_the_user_order():
    taxonomy = _taxonomy(60)
    labels = [_label("Tienda", "Cat050"), _label("Bar", "Cat010")]

    names = [c.name for c in shortlist(taxonomy, "Tienda", labels, cap=10)]

    assert names == sorted(names, key=[c.name for c in taxonomy].index)
