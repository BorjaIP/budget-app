import math

from dashboard.llm.llm_call import bracket_confidence
from dashboard.llm.retrieval import select_similar


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


def _tok(text, logprob):
    return {"token": text, "logprob": logprob}


def test_confidence_is_the_joint_probability_of_the_two_bracketed_tags_only():
    tokens = [
        _tok("Based", -2.0),  # before any bracket: ignored
        _tok("[", math.log(0.9)),
        _tok("Ocio", math.log(0.8)),
        _tok("][", math.log(0.9)),
        _tok("Libros", math.log(0.5)),
        _tok("]", math.log(0.9)),
        _tok(" extra", -3.0),  # after the second tag: ignored
    ]

    assert math.isclose(bracket_confidence(tokens), 0.9 * 0.8 * 0.9 * 0.5 * 0.9, rel_tol=1e-6)


def test_confidence_is_none_without_brackets_or_logprobs():
    assert bracket_confidence([_tok("hello", -0.1)]) is None
    assert bracket_confidence([]) is None
    assert bracket_confidence(None) is None
