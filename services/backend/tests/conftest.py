import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app


@pytest.fixture()
def db_session():
    """Runs each test inside an outer transaction that is always rolled back, even
    though route handlers call db.commit() freely: join_transaction_mode="create_savepoint"
    makes those commits release a SAVEPOINT instead of the real outer transaction, so
    nothing a test does ever lands permanently in the (shared, dev) database."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
