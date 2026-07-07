"""Reminders CRUD, Traccar pull sync, and service-reset push."""

from decimal import Decimal

import httpx
from httpx import Response
from sqlalchemy import select

from app.models import Reminder, ReminderStatus, ServiceType, Vehicle
from tests.conftest import TRACCAR, USER_A, device, mock_accumulators_update, mock_devices, mock_session


def mock_list_maintenances(traccar_mock, items: list[dict]):
    return traccar_mock.get(url__regex=rf"{TRACCAR}/api/maintenances.*").mock(
        return_value=Response(200, json=items)
    )


def mock_maintenance_update(traccar_mock, maintenance_id=77):
    plural = traccar_mock.put(url__regex=rf"{TRACCAR}/api/maintenances/{maintenance_id}").mock(
        return_value=Response(200, json={"id": maintenance_id})
    )
    traccar_mock.put(url__regex=rf"{TRACCAR}/api/maintenance/{maintenance_id}").mock(
        return_value=Response(200, json={"id": maintenance_id})
    )
    return plural


def test_logging_service_resets_traccar_via_singular_api_path(client, db, traccar_mock):
    import json

    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1, odometer_km_cached=Decimal("52.4"))
    service_type = ServiceType(name="prufa 12", default_interval_km=1)
    db.add_all([vehicle, service_type])
    db.flush()
    reminder = Reminder(
        vehicle_id=vehicle.id,
        service_type_id=service_type.id,
        traccar_maintenance_id=1,
        traccar_maintenance_type="totalDistance",
        traccar_maintenance_name="prufa 12",
        interval_km=1,
        last_service_odometer_km=Decimal("41.4"),
        sync_error=True,
        status=ReminderStatus.overdue,
    )
    db.add(reminder)
    db.commit()

    traccar_mock.put(f"{TRACCAR}/api/maintenances/1").mock(
        return_value=Response(404, text="Not Found")
    )
    update = traccar_mock.put(f"{TRACCAR}/api/maintenance/1").mock(
        return_value=Response(200, json={"id": 1})
    )
    mock_accumulators_update(traccar_mock)

    response = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={
            "service_type_id": service_type.id,
            "performed_at": "2026-07-06",
            "odometer_km": "52.4",
        },
    )
    assert response.status_code == 201

    body = client.get(f"/api/v1/vehicles/{vehicle.id}/reminders").json()[0]
    assert body["sync_error"] is False
    assert update.call_count == 1
    payload = json.loads(update.calls.last.request.content)
    assert payload["start"] == 52_400.0


def test_create_reminder_is_local_only(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1, odometer_km_cached=Decimal("50000"))
    service_type = ServiceType(name="Oil change", default_interval_km=15000)
    db.add_all([vehicle, service_type])
    db.commit()

    create_route = traccar_mock.post(f"{TRACCAR}/api/maintenances").mock(
        return_value=Response(200, json={"id": 99})
    )

    response = client.post(
        f"/api/v1/vehicles/{vehicle.id}/reminders",
        json={
            "service_type_id": service_type.id,
            "interval_km": 15000,
            "last_service_odometer_km": "48000",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["traccar_maintenance_id"] is None
    assert body["sync_error"] is False
    assert create_route.call_count == 0


def test_pull_maintenances_creates_reminders(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1, odometer_km_cached=Decimal("50000"))
    db.add(vehicle)
    db.commit()

    mock_list_maintenances(
        traccar_mock,
        [
            {
                "id": 77,
                "name": "Oil change",
                "type": "totalDistance",
                "start": 48_000_000.0,
                "period": 15_000_000.0,
            }
        ],
    )

    response = client.post(f"/api/v1/vehicles/{vehicle.id}/sync-maintenance")
    assert response.status_code == 200
    assert response.json()["created"] == 1

    reminders = client.get(f"/api/v1/vehicles/{vehicle.id}/reminders").json()
    assert len(reminders) == 1
    assert reminders[0]["traccar_maintenance_id"] == 77
    assert reminders[0]["interval_km"] == 15000
    assert float(reminders[0]["last_service_odometer_km"]) == 48000.0

    service_type = db.execute(
        select(ServiceType).where(ServiceType.name == "Oil change")
    ).scalar_one()
    assert service_type is not None


def test_pull_obd_odometer_maintenance(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1, odometer_km_cached=Decimal("120000"))
    db.add(vehicle)
    db.commit()

    traccar_mock.get(url__regex=rf"{TRACCAR}/api/maintenances.*").mock(
        return_value=Response(404)
    )
    traccar_mock.get(url__regex=rf"{TRACCAR}/api/maintenance.*").mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "test for maintenance",
                    "type": "obdOdometer",
                    "start": 100_000.0,
                    "period": 10_000_000.0,
                }
            ],
        )
    )

    response = client.post(f"/api/v1/vehicles/{vehicle.id}/sync-maintenance")
    assert response.status_code == 200
    assert response.json()["created"] == 1

    reminders = client.get(f"/api/v1/vehicles/{vehicle.id}/reminders").json()
    assert len(reminders) == 1
    assert reminders[0]["traccar_maintenance_id"] == 1
    assert reminders[0]["traccar_maintenance_type"] == "obdOdometer"
    assert reminders[0]["traccar_maintenance_name"] == "test for maintenance"
    assert reminders[0]["service_type_name"] == "test for maintenance"
    assert reminders[0]["interval_km"] == 10000
    assert float(reminders[0]["last_service_odometer_km"]) == 100.0


def test_log_service_types_includes_vehicle_reminders(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1)
    traccar_type = ServiceType(name="Oil change")
    local_type = ServiceType(name="Body work")
    db.add_all([vehicle, traccar_type, local_type])
    db.flush()
    db.add(
        Reminder(
            vehicle_id=vehicle.id,
            service_type_id=traccar_type.id,
            traccar_maintenance_id=1,
            traccar_maintenance_type="obdOdometer",
            traccar_maintenance_name="Oil change",
            interval_km=50,
            status=ReminderStatus.ok,
        )
    )
    db.commit()

    response = client.get(f"/api/v1/vehicles/{vehicle.id}/log-service-types")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert "Oil change" in names
    assert "Body work" in names


def test_pull_prunes_removed_traccar_maintenance(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1)
    service_type = ServiceType(name="Oil change")
    db.add_all([vehicle, service_type])
    db.flush()
    reminder = Reminder(
        vehicle_id=vehicle.id,
        service_type_id=service_type.id,
        traccar_maintenance_id=99,
        interval_km=15000,
    )
    db.add(reminder)
    db.commit()
    reminder_id = reminder.id

    mock_list_maintenances(traccar_mock, [])

    client.post(f"/api/v1/vehicles/{vehicle.id}/sync-maintenance")
    db.expire_all()
    assert db.get(Reminder, reminder_id) is None


def test_cannot_edit_traccar_linked_reminder(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1)
    service_type = ServiceType(name="Oil change")
    db.add_all([vehicle, service_type])
    db.flush()
    reminder = Reminder(
        vehicle_id=vehicle.id,
        service_type_id=service_type.id,
        traccar_maintenance_id=77,
        interval_km=15000,
    )
    db.add(reminder)
    db.commit()

    response = client.patch(
        f"/api/v1/reminders/{reminder.id}", json={"interval_km": 20000}
    )
    assert response.status_code == 422


def test_delete_local_reminder_does_not_touch_traccar(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1)
    service_type = ServiceType(name="Oil change")
    db.add_all([vehicle, service_type])
    db.commit()

    reminder_id = client.post(
        f"/api/v1/vehicles/{vehicle.id}/reminders",
        json={"service_type_id": service_type.id, "interval_km": 15000},
    ).json()["id"]

    delete_route = traccar_mock.delete(url__regex=rf"{TRACCAR}/api/maintenances/\d+").mock(
        return_value=Response(204)
    )

    assert client.delete(f"/api/v1/reminders/{reminder_id}").status_code == 204
    assert delete_route.call_count == 0


def test_logging_service_resets_traccar_linked_reminder(client, db, traccar_mock):
    import json

    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1, odometer_km_cached=Decimal("50000"))
    service_type = ServiceType(name="Oil change", default_interval_km=15000)
    db.add_all([vehicle, service_type])
    db.flush()
    reminder = Reminder(
        vehicle_id=vehicle.id,
        service_type_id=service_type.id,
        traccar_maintenance_id=77,
        traccar_maintenance_type="totalDistance",
        traccar_maintenance_name="Oil change",
        interval_km=15000,
        last_service_odometer_km=Decimal("30000"),
        status=ReminderStatus.overdue,
    )
    db.add(reminder)
    db.commit()

    update = mock_maintenance_update(traccar_mock, 77)
    accumulators = mock_accumulators_update(traccar_mock)

    response = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={
            "service_type_id": service_type.id,
            "performed_at": "2026-07-06",
            "odometer_km": "50000",
        },
    )
    assert response.status_code == 201

    body = client.get(f"/api/v1/vehicles/{vehicle.id}/reminders").json()[0]
    assert float(body["last_service_odometer_km"]) == 50000.0
    assert body["status"] == "ok"
    assert update.call_count == 1
    payload = json.loads(update.calls.last.request.content)
    assert payload["start"] == 50_000_000.0
    assert payload["name"] == "Oil change"
    assert payload["type"] == "totalDistance"
    assert accumulators.call_count == 1


def test_create_vehicle_pulls_traccar_maintenance(client, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    mock_list_maintenances(
        traccar_mock,
        [
            {
                "id": 55,
                "name": "Brake service",
                "type": "totalDistance",
                "start": 0,
                "period": 40_000_000.0,
            }
        ],
    )
    create_route = traccar_mock.post(f"{TRACCAR}/api/maintenances").mock(
        return_value=Response(200, json={"id": 99})
    )

    response = client.post("/api/v1/vehicles", json={"traccar_device_id": 1})
    assert response.status_code == 201
    assert create_route.call_count == 0

    vehicle_id = response.json()["id"]
    reminders = client.get(f"/api/v1/vehicles/{vehicle_id}/reminders").json()
    assert len(reminders) == 1
    assert reminders[0]["traccar_maintenance_id"] == 55
