import pytest

from backend.api.auth import ensure_basic_seed
from backend.app import create_app
from backend.config import DevConfig
from backend.extensions import db
from backend import models


@pytest.fixture()
def app(tmp_path):
    db_file = tmp_path / "test.db"
    DevConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_file.as_posix()}"
    DevConfig.JWT_SECRET_KEY = "test-secret-key-0123456789-abcdef"

    _ = models
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        ensure_basic_seed()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
