import asyncio
import json
import math

from dashboard.llm import llm_call
from dashboard.llm.llm_call import categorize_with_confidence, value_confidence
from dashboard.llm.prompt import NONE_OPTION, category_prompt, subcategory_prompt
from dashboard.taxonomy import CategoryEntry, SubEntry, default_taxonomy


def _answer(key: str, value: str, probability: float = 0.9) -> dict:
    """What Ollama returns for a constrained answer, with the value as one token."""
    tokens = [
        {"token": '{ "', "logprob": -9.0},
        {"token": key, "logprob": -0.1},
        {"token": '": "', "logprob": 0.0},
        {"token": value, "logprob": math.log(probability)},
        {"token": '" }', "logprob": -0.5},
    ]
    return {"response": f'{{ "{key}": "{value}" }}', "logprobs": tokens}


def _fake_model(monkeypatch, answers: list[dict]) -> list[dict]:
    calls: list[dict] = []

    async def fake(prompt, model=llm_call.DEFAULT_MODEL, schema=None, timeout=0):
        calls.append({"prompt": prompt, "schema": schema})
        return answers[len(calls) - 1]

    monkeypatch.setattr(llm_call, "query_llm_detailed", fake)
    return calls


def test_value_confidence_counts_only_the_tokens_of_the_answered_value():
    answer = _answer("category", "Ocio", 0.8)

    assert math.isclose(value_confidence(answer["response"], answer["logprobs"], "category"), 0.8, rel_tol=1e-9)


def test_value_confidence_is_none_when_tokens_do_not_rebuild_the_response():
    answer = _answer("category", "Ocio")

    assert value_confidence(answer["response"] + "x", answer["logprobs"], "category") is None
    assert value_confidence("not json", [{"token": "not json", "logprob": -1.0}], "category") is None
    assert value_confidence(answer["response"], None, "category") is None


def test_two_steps_give_category_subcategory_and_the_product_of_their_probabilities(monkeypatch):
    calls = _fake_model(monkeypatch, [_answer("category", "Ocio", 0.9), _answer("subcategory", "Libros", 0.5)])

    result = asyncio.run(categorize_with_confidence("Libreria Central", default_taxonomy()))

    assert result[:2] == ("Ocio", "Libros")
    assert math.isclose(result[2], 0.45, rel_tol=1e-9)
    assert calls[0]["schema"]["properties"]["category"]["enum"][0] == "Deuda"
    assert "Libros" in calls[1]["schema"]["properties"]["subcategory"]["enum"]
    assert NONE_OPTION in calls[1]["schema"]["properties"]["subcategory"]["enum"]


def test_answering_none_keeps_only_the_parent_category(monkeypatch):
    _fake_model(monkeypatch, [_answer("category", "Ocio"), _answer("subcategory", NONE_OPTION)])

    category, subcategory, _ = asyncio.run(categorize_with_confidence("Algo raro", default_taxonomy()))

    assert (category, subcategory) == ("Ocio", None)


def test_a_category_without_subcategories_needs_a_single_call(monkeypatch):
    taxonomy = [CategoryEntry("Mascotas"), CategoryEntry("Ocio", subcategories=[SubEntry("Libros"), SubEntry("Cine")])]
    calls = _fake_model(monkeypatch, [_answer("category", "Mascotas", 0.7)])

    category, subcategory, confidence = asyncio.run(categorize_with_confidence("Veterinario", taxonomy))

    assert (category, subcategory) == ("Mascotas", None)
    assert len(calls) == 1 and math.isclose(confidence, 0.7, rel_tol=1e-9)


def test_a_taxonomy_with_one_category_never_asks_for_it(monkeypatch):
    taxonomy = [CategoryEntry("Todo", subcategories=[SubEntry("A"), SubEntry("B")])]
    calls = _fake_model(monkeypatch, [_answer("subcategory", "B", 0.6)])

    category, subcategory, _ = asyncio.run(categorize_with_confidence("x", taxonomy))

    assert (category, subcategory) == ("Todo", "B") and len(calls) == 1


def test_an_unreadable_answer_falls_back_to_otros_general_with_zero_confidence(monkeypatch):
    _fake_model(monkeypatch, [{"response": "I think it is leisure", "logprobs": []}])

    assert asyncio.run(categorize_with_confidence("x", default_taxonomy())) == ("Otros", "General", 0.0)


def test_prompts_list_names_descriptions_and_examples_from_the_taxonomy():
    taxonomy = [CategoryEntry("Mascotas", "veterinario y comida de animales"), CategoryEntry("Ocio")]
    ocio = CategoryEntry("Ocio", subcategories=[SubEntry("Libros", "novelas y ensayo"), SubEntry("Cine")])

    first = category_prompt(taxonomy, [("Clinica Vet Sol", "Mascotas")], "Pienso Perros SL")
    second = subcategory_prompt(ocio, [("Libreria Central", "Libros")], "Casa del Libro")

    assert "- Mascotas: veterinario y comida de animales" in first and "- Ocio\n" in first
    assert "operation: Clinica Vet Sol\ncategory: Mascotas" in first and first.endswith("operation: Pienso Perros SL\ncategory:")
    assert '- Libros: novelas y ensayo' in second and "(ninguna)" in second
    assert "operation: Libreria Central\nsubcategory: Libros" in second


def test_the_prompt_size_grows_with_names_not_with_every_subcategory():
    many = [CategoryEntry(f"Categoria {i}", subcategories=[SubEntry(f"Sub {i}-{j}") for j in range(30)]) for i in range(100)]

    prompt = category_prompt(many, [], "x")

    assert "Sub 3-4" not in prompt and len(prompt) < 4000


def test_a_positive_amount_is_offered_income_and_saving_categories_and_otros(monkeypatch):
    calls = _fake_model(monkeypatch, [_answer("category", "Nómina", 0.9)])

    result = asyncio.run(categorize_with_confidence("Transferencia Empresa Faro", default_taxonomy(), amount=2100.0))

    assert result[:2] == ("Nómina", None)
    assert calls[0]["schema"]["properties"]["category"]["enum"] == ["Nómina", "Ahorro", "Otros"]


def test_a_negative_amount_is_never_offered_income_categories(monkeypatch):
    calls = _fake_model(monkeypatch, [_answer("category", "Ocio", 0.9), _answer("subcategory", "Libros", 0.9)])

    asyncio.run(categorize_with_confidence("Libreria", default_taxonomy(), amount=-12.0))

    assert "Nómina" not in calls[0]["schema"]["properties"]["category"]["enum"]
