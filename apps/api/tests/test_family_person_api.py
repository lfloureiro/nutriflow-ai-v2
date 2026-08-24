from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_family_and_person_api(db_session: Session) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)

    try:
        with TestClient(app) as client:
            family_response = client.post(
                "/api/families",
                json={
                    "name": "Test Family",
                    "timezone": "Europe/Lisbon",
                },
            )

            assert family_response.status_code == 201

            family = family_response.json()
            family_id = family["id"]

            person_response = client.post(
                f"/api/families/{family_id}/persons",
                json={
                    "first_name": "Test",
                    "last_name": "Person",
                    "birth_date": date(1990, 1, 1).isoformat(),
                    "preferred_locale": "pt-PT",
                    "timezone": "Europe/Lisbon",
                },
            )

            assert person_response.status_code == 201

            person = person_response.json()
            person_id = person["id"]

            assert person["family_id"] == family_id

            list_response = client.get(f"/api/families/{family_id}/persons")

            assert list_response.status_code == 200
            assert len(list_response.json()) == 1

            get_person_response = client.get(f"/api/persons/{person_id}")

            assert get_person_response.status_code == 200
            assert get_person_response.json()["first_name"] == "Test"

            updated_response = client.patch(
                f"/api/persons/{person_id}",
                json={
                    "first_name": "Ana",
                    "last_name": "Atualizada",
                    "timezone": "Europe/Madrid",
                },
            )

            assert updated_response.status_code == 200
            updated = updated_response.json()
            assert updated["first_name"] == "Ana"
            assert updated["last_name"] == "Atualizada"
            assert updated["timezone"] == "Europe/Madrid"
            assert updated["family_id"] == family_id

    finally:
        app.dependency_overrides.clear()


def test_invalid_timezone_is_rejected(db_session: Session) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)

    try:
        with TestClient(app) as client:
            invalid_family = client.post(
                "/api/families",
                json={"name": "Bad timezone", "timezone": "Europe/Not-A-Place"},
            )
            assert invalid_family.status_code == 422

            family_response = client.post(
                "/api/families",
                json={"name": "Valid family", "timezone": "Europe/Lisbon"},
            )
            assert family_response.status_code == 201
            family_id = family_response.json()["id"]

            invalid_person = client.post(
                f"/api/families/{family_id}/persons",
                json={
                    "first_name": "Invalid",
                    "birth_date": "1990-01-01",
                    "timezone": "Mars/Olympus_Mons",
                },
            )
            assert invalid_person.status_code == 422
    finally:
        app.dependency_overrides.clear()
