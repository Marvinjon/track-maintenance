"""Bulk CSV import for parts."""

from decimal import Decimal

from sqlalchemy import func, select

from app.models import Part, StockMovement
from tests.conftest import USER_A, mock_session


def _login(client, traccar_mock):
    mock_session(traccar_mock, USER_A)
    client.cookies.set("JSESSIONID", "user-a")


def test_import_parts_creates_with_initial_stock(client, db, traccar_mock):
    _login(client, traccar_mock)

    response = client.post(
        "/api/v1/parts/import",
        json={
            "rows": [
                {
                    "sku": "OF-1",
                    "name": "Oil filter",
                    "unit": "pcs",
                    "min_stock": "2",
                    "unit_cost": "25.50",
                    "initial_stock": "10",
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert data["skipped"] == 0
    assert data["errors"] == []

    part = db.execute(select(Part).where(Part.sku == "OF-1")).scalar_one()
    assert part.name == "Oil filter"
    assert part.min_stock == Decimal("2")
    assert part.unit_cost == Decimal("25.50")

    stock = db.execute(
        select(func.sum(StockMovement.quantity)).where(StockMovement.part_id == part.id)
    ).scalar_one()
    assert stock == Decimal("10")


def test_import_parts_skips_duplicate_sku(client, db, traccar_mock):
    _login(client, traccar_mock)
    db.add(Part(name="Existing", sku="OF-1"))
    db.commit()

    response = client.post(
        "/api/v1/parts/import",
        json={"rows": [{"sku": "OF-1", "name": "Duplicate", "unit": "", "min_stock": "", "unit_cost": "", "initial_stock": ""}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 0
    assert data["skipped"] == 1
    assert data["errors"] == []


def test_import_parts_without_initial_stock(client, db, traccar_mock):
    _login(client, traccar_mock)

    response = client.post(
        "/api/v1/parts/import",
        json={
            "rows": [
                {
                    "sku": "",
                    "name": "Wiper blade",
                    "unit": "pcs",
                    "min_stock": "0",
                    "unit_cost": "",
                    "initial_stock": "",
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1

    part = db.execute(select(Part).where(Part.name == "Wiper blade")).scalar_one()
    stock = db.execute(
        select(func.sum(StockMovement.quantity)).where(StockMovement.part_id == part.id)
    ).scalar_one()
    assert stock is None
