from dashboard.llm.llm_call import build_few_shot_examples, parse_category_response
from dashboard.llm.prompt import STATIC_EXAMPLES


class TestParseCategoryResponse:
    def test_two_brackets_happy_path(self):
        assert parse_category_response("[Gastos diarios][Restaurantes]") == (
            "Gastos diarios",
            "Restaurantes",
        )

    def test_two_brackets_with_surrounding_text(self):
        raw = "Sure, here is the category: [Transporte][Taxi/Uber] done."
        assert parse_category_response(raw) == ("Transporte", "Taxi/Uber")

    def test_single_bracket_subcategory_maps_to_parent(self):
        assert parse_category_response("[Restaurantes]") == (
            "Gastos diarios",
            "Restaurantes",
        )

    def test_single_bracket_category_maps_to_first_subcategory(self):
        assert parse_category_response("[Transporte]") == ("Transporte", "Combustible")

    def test_empty_input_falls_back(self):
        assert parse_category_response("") == ("Otros", "General")

    def test_garbage_input_falls_back(self):
        assert parse_category_response("no brackets here") == ("Otros", "General")

    def test_invalid_two_bracket_pair_falls_back(self):
        assert parse_category_response("[NotACategory][NotASubcategory]") == (
            "Otros",
            "General",
        )

    def test_valid_category_invalid_subcategory_falls_back(self):
        assert parse_category_response("[Transporte][Bicicleta]") == (
            "Otros",
            "General",
        )


class TestBuildFewShotExamples:
    def test_falls_back_to_static_when_no_rows(self):
        assert build_few_shot_examples([]) == STATIC_EXAMPLES

    def test_falls_back_to_static_when_fewer_than_three_valid_rows(self):
        rows = [
            {"concept": "Bizum a Marta", "category": "Gastos diarios", "subcategory": "Comida"},
            {"concept": "Netflix", "category": "Gastos diarios", "subcategory": "Suscripciones"},
        ]
        assert build_few_shot_examples(rows) == STATIC_EXAMPLES

    def test_ignores_rows_with_invalid_taxonomy(self):
        rows = [
            {"concept": "Bizum a Marta", "category": "Gastos diarios", "subcategory": "Comida"},
            {"concept": "Netflix", "category": "Gastos diarios", "subcategory": "Suscripciones"},
            {"concept": "Bad row", "category": "NotReal", "subcategory": "NotReal"},
            {"concept": "Uber", "category": "Transporte", "subcategory": "Taxi/Uber"},
        ]
        # Only 3 valid rows -> below the 3-row threshold is false (3 is enough)
        result = build_few_shot_examples(rows)
        assert result != STATIC_EXAMPLES
        assert "Bad row" not in result

    def test_formats_valid_examples_correctly(self):
        rows = [
            {"concept": "Bizum a Marta", "category": "Gastos diarios", "subcategory": "Comida"},
            {"concept": "Netflix", "category": "Gastos diarios", "subcategory": "Suscripciones"},
            {"concept": "Uber", "category": "Transporte", "subcategory": "Taxi/Uber"},
        ]
        result = build_few_shot_examples(rows)
        assert result.startswith("Examples:")
        assert "operation: Bizum a Marta" in result
        assert "→ [Gastos diarios][Comida]" in result
        assert "operation: Uber" in result
        assert "→ [Transporte][Taxi/Uber]" in result

    def test_prefers_one_example_per_distinct_category_up_to_limit(self):
        rows = [
            {"concept": f"Concept {i}", "category": "Gastos diarios", "subcategory": "Comida"}
            for i in range(5)
        ] + [
            {"concept": "Uber", "category": "Transporte", "subcategory": "Taxi/Uber"},
            {"concept": "Netflix", "category": "Ocio", "subcategory": "Otros"},
        ]
        result = build_few_shot_examples(rows, limit=2)
        # Should prefer distinct categories first: Gastos diarios + Transporte
        assert "Uber" in result
        assert "Concept 0" in result
