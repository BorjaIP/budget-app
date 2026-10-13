from dashboard.llm.run_stats import RunStats


def test_summary_counts_fallbacks_errors_and_categories():
    stats = RunStats()
    stats.record("Ocio", "Libros", 200.0)
    stats.record("Ocio", "Conciertos o espectáculos", 400.0)
    stats.record("Otros", "General", 300.0)
    stats.record_error()

    summary = stats.summary()

    assert "3 categorized" in summary
    assert "1 fell back to Otros/General" in summary
    assert "1 errors" in summary
    assert "avg 300 ms/call" in summary
    assert "Ocio=2" in summary and "Otros=1" in summary


def test_summary_of_an_empty_run_does_not_divide_by_zero():
    assert "0 categorized" in RunStats().summary()
    assert "top categories: none" in RunStats().summary()
