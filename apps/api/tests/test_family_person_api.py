from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app


def test_family_and_person_api(db_session: Session) -> None:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

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

            list_response = client.get(
                f"/api/families/{family_id}/persons"
            )

            assert list_response.status_code == 200
            assert len(list_response.json()) == 1

            get_person_response = client.get(
                f"/api/persons/{person_id}"
            )

            assert get_person_response.status_code == 200
            assert get_person_response.json()["first_name"] == "Test"

    finally:
        app.dependency_overrides.clear()

