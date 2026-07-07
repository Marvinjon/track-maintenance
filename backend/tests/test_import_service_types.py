"""Bulk CSV import for service types."""

from sqlalchemy import select

from app.models import ServiceType
from tests.conftest import USER_A, mock_session


def _login(client, traccar_mock):
    mock_session(traccar_mock, USER_A)
    client.cookies.set("JSESSIONID", "user-a")


def test_import_service_types_creates_new(client, db, traccar_mock):
    _login(client, traccar_mock)

    response = client.post(
        "/api/v1/service-types/import",
        json={
            "rows": [
                {"name": "Oil change", "default_interval_km": "10000", "default_interval_days": "365"},
                {"name": "Brake service", "default_interval_km": "", "default_interval_days": ""},
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 2
    assert data["skipped"] == 0
    assert data["errors"] == []

    types = db.execute(select(ServiceType).order_by(ServiceType.name)).scalars().all()
    assert len(types) == 2
    oil = next(t for t in types if t.name == "Oil change")
    assert oil.default_interval_km == 10000
    assert oil.default_interval_days == 365


def test_import_service_types_skips_duplicate(client, db, traccar_mock):
    _login(client, traccar_mock)
    db.add(ServiceType(name="Oil change"))
    db.commit()

    response = client.post(
        "/api/v1/service-types/import",
        json={"rows": [{"name": "Oil change", "default_interval_km": "", "default_interval_days": ""}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 0
    assert data["skipped"] == 1
    assert data["errors"] == []


def test_import_service_types_reports_invalid_row(client, traccar_mock):
    _login(client, traccar_mock)

    response = client.post(
        "/api/v1/service-types/import",
        json={
            "rows": [
                {"name": "", "default_interval_km": "", "default_interval_days": ""},
                {"name": "Tire change", "default_interval_km": "bad", "default_interval_days": ""},
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 0
    assert data["skipped"] == 0
    assert len(data["errors"]) == 2
