import importlib
import sys

import reflex as rx


def test_default_database_lives_under_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    manager = DatabaseManager()
    manager.engine.dispose()

    assert (tmp_path / "data" / "expenses.db").exists()
    assert not (tmp_path / "expenses.db").exists()


def test_rxconfig_points_uploads_to_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REFLEX_UPLOADED_FILES_DIR", raising=False)
    monkeypatch.syspath_prepend(str(__import__("pathlib").Path(__file__).parent.parent))
    sys.modules.pop("rxconfig", None)
    try:
        importlib.import_module("rxconfig")
        upload_dir = rx.get_upload_dir()
    finally:
        sys.modules.pop("rxconfig", None)

    assert upload_dir.as_posix().endswith("data/uploaded_files")
    assert upload_dir.is_dir()


def test_rxconfig_keeps_explicit_upload_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REFLEX_UPLOADED_FILES_DIR", str(tmp_path / "custom"))
    monkeypatch.syspath_prepend(str(__import__("pathlib").Path(__file__).parent.parent))
    sys.modules.pop("rxconfig", None)
    try:
        importlib.import_module("rxconfig")
        upload_dir = rx.get_upload_dir()
    finally:
        sys.modules.pop("rxconfig", None)

    assert upload_dir == tmp_path / "custom"


def test_file_processor_default_temp_folder_is_under_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.utils.file_processor import FileProcessor

    processor = FileProcessor()

    assert processor.temp_folder.as_posix() == "data/temp_uploads"
    assert (tmp_path / "data" / "temp_uploads").is_dir()
