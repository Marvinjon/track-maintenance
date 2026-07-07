"""Parts CRUD, manual movements ledger, low-stock views."""

import pytest

from tests.conftest import USER_A, mock_devices, mock_session


@pytest.fixture
def logged_in(client, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [])
    client.cookies.set("JSESSIONID", "user-a")
    return client


def _create_part(client, **overrides):
    payload = {"name": "Oil filter", "sku": "OF-1", "min_stock": "2"}
    payload.update(overrides)
    response = client.post("/api/v1/parts", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_and_list_parts(logged_in):
    part = _create_part(logged_in)
    assert part["current_stock"] == "0"
    assert part["low_stock"] is True  # 0 < min_stock 2

    body = logged_in.get("/api/v1/parts").json()
    assert [p["name"] for p in body] == ["Oil filter"]


def test_duplicate_sku_409(logged_in):
    _create_part(logged_in)
    response = logged_in.post("/api/v1/parts", json={"name": "Other", "sku": "OF-1"})
    assert response.status_code == 409


def test_current_stock_is_sum_of_movements(logged_in):
    part = _create_part(logged_in)

    logged_in.post(
        f"/api/v1/parts/{part['id']}/movements",
        json={"quantity": "10", "reason": "purchase"},
    )
    logged_in.post(
        f"/api/v1/parts/{part['id']}/movements",
        json={"quantity": "-3", "reason": "adjustment", "note": "shrinkage"},
    )
    logged_in.post(
        f"/api/v1/parts/{part['id']}/movements",
        json={"quantity": "1", "reason": "return"},
    )

    body = logged_in.get("/api/v1/parts").json()
    assert float(body[0]["current_stock"]) == 8.0  # 10 - 3 + 1
    assert body[0]["low_stock"] is False


def test_manual_movement_cannot_use_used_in_service(logged_in):
    part = _create_part(logged_in)
    response = logged_in.post(
        f"/api/v1/parts/{part['id']}/movements",
        json={"quantity": "-1", "reason": "used_in_service"},
    )
    assert response.status_code == 422


def test_zero_quantity_movement_rejected(logged_in):
    part = _create_part(logged_in)
    response = logged_in.post(
        f"/api/v1/parts/{part['id']}/movements",
        json={"quantity": "0", "reason": "purchase"},
    )
    assert response.status_code == 422


def test_ledger_pagination_newest_first(logged_in):
    part = _create_part(logged_in)
    for quantity in ("1", "2", "3"):
        logged_in.post(
            f"/api/v1/parts/{part['id']}/movements",
            json={"quantity": quantity, "reason": "purchase"},
        )

    body = logged_in.get(f"/api/v1/parts/{part['id']}/movements?limit=2").json()
    assert body["total"] == 3
    assert [float(m["quantity"]) for m in body["items"]] == [3.0, 2.0]


def test_archive_part_hides_from_list(logged_in):
    part = _create_part(logged_in)
    assert logged_in.delete(f"/api/v1/parts/{part['id']}").status_code == 204

    assert logged_in.get("/api/v1/parts").json() == []
    archived = logged_in.get("/api/v1/parts?include_archived=true").json()
    assert archived[0]["archived"] is True


def test_low_stock_endpoint(logged_in):
    low = _create_part(logged_in, name="Brake pads", sku="BP-1", min_stock="4")
    ok = _create_part(logged_in, name="Wiper blade", sku="WB-1", min_stock="1")
    logged_in.post(
        f"/api/v1/parts/{low['id']}/movements",
        json={"quantity": "2", "reason": "purchase"},
    )
    logged_in.post(
        f"/api/v1/parts/{ok['id']}/movements",
        json={"quantity": "5", "reason": "purchase"},
    )

    body = logged_in.get("/api/v1/stock/low").json()

    assert [p["name"] for p in body] == ["Brake pads"]
    assert float(body[0]["current_stock"]) == 2.0
