from dashboard.expenses.state import highlight_segments


def test_matches_are_flagged_case_insensitively_and_keep_the_original_text():
    assert highlight_segments("Recibo LUZ norte", "luz") == [
        {"t": "Recibo ", "m": False},
        {"t": "LUZ", "m": True},
        {"t": " norte", "m": False},
    ]


def test_every_occurrence_is_flagged():
    segments = highlight_segments("ana y ANA", "ana")

    assert [s["t"] for s in segments if s["m"]] == ["ana", "ANA"]


def test_no_term_or_no_match_returns_the_text_unchanged():
    assert highlight_segments("Cafetería", "") == [{"t": "Cafetería", "m": False}]
    assert highlight_segments("Cafetería", "zzz") == [{"t": "Cafetería", "m": False}]
