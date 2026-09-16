from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.demo_seed import DEMO_PERSON_ID, seed_demo_dataset
from app.main import app


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_extract_document_endpoint_returns_source_text(db_session: Session) -> None:
    seed_demo_dataset(db_session)
    db_session.commit()
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{DEMO_PERSON_ID}/nutrition-plan-imports/extract-document",
                files={
                    "document": (
                        "plano.txt",
                        "Pequeno-almoço: proteína mínimo 30 g.\nLegumes ao almoço e jantar.",
                        "text/plain",
                    )
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["filename"] == "plano.txt"
        assert payload["document_type"] == "text"
        assert "proteína mínimo 30 g" in payload["source_text"]
        assert payload["extractor_name"] == "nutriflow-document-text"
    finally:
        app.dependency_overrides.clear()


def test_extract_document_endpoint_rejects_unsupported_file(db_session: Session) -> None:
    seed_demo_dataset(db_session)
    db_session.commit()
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/persons/{DEMO_PERSON_ID}/nutrition-plan-imports/extract-document",
                files={"document": ("plano.jpg", b"fake", "image/jpeg")},
            )

        assert response.status_code == 422
        assert "Unsupported document type" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
