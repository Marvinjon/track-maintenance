import httpx
from httpx import Response

from tests.conftest import TRACCAR


def test_health_ok(client, traccar_mock):
    traccar_mock.get(f"{TRACCAR}/api/server").mock(return_value=Response(200, json={}))

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["traccar_reachable"] is True
    assert body["traccar_public_url"] is None


def test_health_reports_traccar_down_but_still_200(client, traccar_mock):
    traccar_mock.get(f"{TRACCAR}/api/server").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["traccar_reachable"] is False
