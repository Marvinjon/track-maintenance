"""record_parts <-> stock movements atomicity and the stock = SUM invariant."""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import MaintenanceRecord, Part, RecordPart, ServiceType, StockMovement, Vehicle
from tests.conftest import USER_A, device, mock_devices, mock_session


@pytest.fixture
def setup(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1, plate="AB-123")
    service_type = ServiceType(name="Oil change")
    part = Part(name="Oil filter", sku="OF-1", min_stock=Decimal("1"))
    db.add_all([vehicle, service_type, part])
    db.commit()
    return {"vehicle": vehicle, "service_type": service_type, "part": part}


def _stock(client, part_id):
    parts = client.get("/api/v1/parts").json()
    return float(next(p for p in parts if p["id"] == part_id)["current_stock"])


def _purchase(client, part_id, quantity):
    response = client.post(
        f"/api/v1/parts/{part_id}/movements",
        json={"quantity": str(quantity), "reason": "purchase"},
    )
    assert response.status_code == 201


def test_record_with_parts_creates_negative_movements(client, db, setup):
    part = setup["part"]
    _purchase(client, part.id, 10)

    response = client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "parts": [{"part_id": part.id, "quantity": "2"}],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["parts"]) == 1
    assert body["parts"][0]["part_id"] == part.id
    assert body["parts"][0]["part_name"] == "Oil filter"
    assert float(body["parts"][0]["quantity"]) == 2.0
    assert _stock(client, part.id) == 8.0

    movement = db.execute(
        select(StockMovement).where(StockMovement.reason == "used_in_service")
    ).scalar_one()
    assert float(movement.quantity) == -2.0
    assert movement.maintenance_record_id == body["id"]


def test_stock_is_always_sum_of_ledger(client, db, setup):
    """The invariant: current_stock reported by the API == SUM(quantity)."""
    part = setup["part"]
    _purchase(client, part.id, 5)
    client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "parts": [{"part_id": part.id, "quantity": "3"}],
        },
    )
    client.post(
        f"/api/v1/parts/{part.id}/movements",
        json={"quantity": "-1", "reason": "adjustment"},
    )

    ledger_sum = db.execute(
        select(func.sum(StockMovement.quantity)).where(StockMovement.part_id == part.id)
    ).scalar_one()

    assert float(ledger_sum) == 1.0  # 5 - 3 - 1
    assert _stock(client, part.id) == float(ledger_sum)


def test_stock_may_go_negative(client, setup):
    """Using more than is in stock is allowed (frontend warns, backend permits)."""
    part = setup["part"]

    response = client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "parts": [{"part_id": part.id, "quantity": "4"}],
        },
    )

    assert response.status_code == 201
    assert _stock(client, part.id) == -4.0


def test_failed_record_creation_rolls_back_everything(client, db, setup):
    """One invalid part id mid-list -> 422 and NO record, record_parts or
    movements are persisted (single transaction)."""
    part = setup["part"]
    _purchase(client, part.id, 10)

    response = client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "parts": [
                {"part_id": part.id, "quantity": "2"},  # valid, applied first
                {"part_id": 99999, "quantity": "1"},  # invalid -> abort
            ],
        },
    )

    assert response.status_code == 422
    db.expire_all()
    assert db.execute(select(func.count()).select_from(MaintenanceRecord)).scalar_one() == 0
    assert db.execute(select(func.count()).select_from(RecordPart)).scalar_one() == 0
    # Only the purchase movement exists; the partial used_in_service one rolled back.
    reasons = db.execute(select(StockMovement.reason)).scalars().all()
    assert reasons == ["purchase"]
    assert _stock(client, part.id) == 10.0


def test_delete_record_reverses_stock(client, db, setup):
    part = setup["part"]
    _purchase(client, part.id, 10)

    record_id = client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "parts": [{"part_id": part.id, "quantity": "2"}],
        },
    ).json()["id"]
    assert _stock(client, part.id) == 8.0

    assert client.delete(f"/api/v1/records/{record_id}").status_code == 204

    # Stock restored via a compensating 'return' movement; ledger is append-only.
    assert _stock(client, part.id) == 10.0
    db.expire_all()
    reasons = sorted(db.execute(select(StockMovement.reason)).scalars().all())
    assert reasons == ["purchase", "return", "used_in_service"]
    assert db.execute(select(func.count()).select_from(RecordPart)).scalar_one() == 0


def test_delete_record_with_parts_and_change_history(client, setup):
    part = setup["part"]
    _purchase(client, part.id, 10)

    record_id = client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "parts": [{"part_id": part.id, "quantity": "2"}],
        },
    ).json()["id"]

    patch = client.patch(
        f"/api/v1/records/{record_id}",
        json={"notes": "Adjusted after inspection"},
    )
    assert patch.status_code == 200
    detail = client.get(f"/api/v1/records/{record_id}")
    assert len(detail.json()["changes"]) == 1

    assert client.delete(f"/api/v1/records/{record_id}").status_code == 204
    assert client.get(f"/api/v1/records/{record_id}").status_code == 404
    assert _stock(client, part.id) == 10.0


def test_patch_record_replaces_parts_and_adjusts_stock(client, db, setup):
    part = setup["part"]
    other = Part(name="Air filter", sku="AF-1")
    db.add(other)
    db.commit()

    _purchase(client, part.id, 10)
    _purchase(client, other.id, 10)

    record_id = client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "parts": [{"part_id": part.id, "quantity": "2"}],
        },
    ).json()["id"]

    response = client.patch(
        f"/api/v1/records/{record_id}",
        json={"parts": [{"part_id": other.id, "quantity": "1"}]},
    )

    assert response.status_code == 200
    new_parts = response.json()["parts"]
    assert [(p["part_id"], p["part_name"], float(p["quantity"])) for p in new_parts] == [
        (other.id, "Air filter", 1.0)
    ]
    assert _stock(client, part.id) == 10.0  # reversed back
    assert _stock(client, other.id) == 9.0  # newly consumed
