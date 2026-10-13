import pandas as pd

from dashboard.database.models import ExpenseCreate


def _write_export(path):
    pd.DataFrame(
        {
            "FECHA OPERACIÓN": ["01/03/2026", "05/03/2026", "09/03/2026"],
            "FECHA VALOR": ["01/03/2026", "05/03/2026", "09/03/2026"],
            "CONCEPTO": ["Nómina marzo", "Recibo luz", "Cafetería Sol"],
            "IMPORTE": [1500.0, -80.5, -3.2],
            "SALDO": [2500.0, 2419.5, 2416.3],
        }
    ).to_excel(path, index=False)


def test_preview_reports_counts_range_and_totals_without_storing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database import operations
    from dashboard.database.operations import DatabaseManager
    from dashboard.utils.file_processor import FileProcessor

    manager = DatabaseManager(database_url=f"sqlite:///{tmp_path}/expenses.db")
    monkeypatch.setattr(operations, "db_manager", manager)
    monkeypatch.setattr("dashboard.utils.file_processor.db_manager", manager)
    export = tmp_path / "bbva_marzo.xlsx"
    _write_export(export)
    processor = FileProcessor(temp_folder=str(tmp_path / "tmp"))

    preview = processor.preview_excel_file(str(export))

    assert preview["status"] == "success"
    assert (preview["total"], preview["new"], preview["duplicates"]) == (3, 3, 0)
    assert (preview["date_from"], preview["date_to"]) == ("2026-03-01", "2026-03-09")
    assert (preview["income"], preview["spending"]) == (1500.0, 83.7)
    assert manager.get_recent_expenses(limit=5) == []

    processor.process_excel_file(str(export))
    again = processor.preview_excel_file(str(export))
    assert (again["new"], again["duplicates"]) == (0, 3)


def test_preview_rejects_an_unreadable_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.utils.file_processor import FileProcessor

    broken = tmp_path / "roto.xlsx"
    broken.write_bytes(b"not a spreadsheet")

    result = FileProcessor(temp_folder=str(tmp_path / "tmp")).preview_excel_file(str(broken))

    assert result["status"] == "error"
