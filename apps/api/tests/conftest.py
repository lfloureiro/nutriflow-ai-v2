from collections.abc import Iterator

import pytest
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import Family


def _clear_application_data(connection: Connection) -> None:
    for table in reversed(Family.metadata.sorted_tables):
        connection.execute(table.delete())


@pytest.fixture
def db_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    _clear_application_data(connection)

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
