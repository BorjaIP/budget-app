import math

from dashboard.llm.retrieval import SimilarityIndex, confident_match, select_similar


def _label(concept, category="Ocio", sub="Libros", confirmations=1):
    return {"concept": concept, "category": category, "subcategory": sub, "confirmations": confirmations}


def test_the_closest_label_goes_last_and_unrelated_ones_only_fill_the_rest():
    labels = [
        _label("Libreria Central Madrid"),
        _label("Gasolinera Norte", "Transporte", "Gasolina"),
        _label("Recibo Luz Sol", "Servicios básicos", "Electricidad"),
    ]

    picked = select_similar("Pago Movil En Gasolinera Norte Sur", labels, limit=2)

    assert [p["concept"] for p in picked][-1] == "Gasolinera Norte"
    assert len(picked) == 2


def test_a_shared_rare_word_beats_a_shared_common_word():
    labels = [_label(f"Pago tienda {i}") for i in range(5)] + [_label("Pago Lush Alcala", "Salud/médicos", "Cuidado")]

    picked = select_similar("Pago Lush", labels, limit=1)

    assert picked[0]["concept"] == "Pago Lush Alcala"


def test_without_overlap_the_most_confirmed_labels_are_used():
    labels = [_label("Aaa", confirmations=1), _label("Bbb", confirmations=7)]

    assert select_similar("zzz", labels, limit=1)[0]["concept"] == "Bbb"
    assert select_similar("zzz", [], limit=3) == []


def test_similarity_tolerates_typos_and_bank_noise():
    index = SimilarityIndex([_label("Pago Movil En Panaderia Norte, Madrid, Tarj. :*0001"), _label("Gasolinera Ribera")])

    score, best = index.search("Compra Panadria Norte 0425", k=1)[0]

    assert best["concept"].startswith("Pago Movil En Panaderia Norte")
    assert score > 0.7


def test_confident_match_needs_a_high_score_and_no_disagreeing_rival():
    sure = _label("Panaderia Norte", "Gastos diarios", "Comida")
    other = _label("Panaderia Norte Sur", "Ocio", "Libros")

    assert confident_match([(0.95, sure)])[1] is sure
    assert confident_match([(0.80, sure)]) is None
    assert confident_match([(0.95, sure), (0.75, other)]) is None
    assert confident_match([(0.95, sure), (0.75, _label("Panaderia Norte 2", "Gastos diarios", "Comida"))]) is not None
    assert confident_match([]) is None
