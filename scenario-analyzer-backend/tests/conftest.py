import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _db_isolation(monkeypatch, tmp_path):
    import app.config as app_config
    from app.database import init_db, reset_engine

    db_path = tmp_path / "scenario_test.db"
    monkeypatch.setattr(app_config.settings, "DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()
    yield
    reset_engine()


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
