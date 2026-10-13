import importlib

import pytest


@pytest.fixture
def fresh_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no .env and no data/ in the cwd
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    import dashboard.config as config

    return importlib.reload(config)


def test_settings_defaults(fresh_config):
    settings = fresh_config.Settings()
    assert settings.database_url == "sqlite:///data/expenses.db"
    assert settings.ollama_base_url == "http://localhost:11434"


def test_settings_read_environment_overrides(fresh_config, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/x")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    settings = fresh_config.Settings()
    assert settings.database_url == "postgresql+psycopg2://u:p@db:5432/x"
    assert settings.ollama_base_url == "http://ollama:11434"


def test_database_manager_creates_engine_lazily_for_sqlite_url(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from dashboard.database.operations import DatabaseManager

    target = tmp_path / "nested" / "expenses.db"
    manager = DatabaseManager(database_url=f"sqlite:///{target}")
    assert not target.exists()  # nothing is opened until the engine is used

    manager.engine
    assert target.exists()
