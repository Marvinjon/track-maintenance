"""Auth dependency: Traccar session passthrough, caching, 401 mapping."""

from httpx import Response

from tests.conftest import TRACCAR, USER_A, mock_devices, mock_session


def test_missing_credentials_returns_401(client, traccar_mock):
    response = client.get("/api/v1/vehicles")
    assert response.status_code == 401


def test_maint_session_cookie_is_accepted(client, traccar_mock):
    session_route = mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [])

    client.cookies.set("maint_session", "abc123")
    response = client.get("/api/v1/vehicles")

    assert response.status_code == 200
    forwarded = session_route.calls.last.request.headers.get("cookie", "")
    assert "JSESSIONID=abc123" in forwarded


def test_login_success_sets_maint_session_cookie(client, traccar_mock):
    traccar_mock.post(f"{TRACCAR}/api/session").mock(
        return_value=Response(
            200,
            json=USER_A,
            headers={"set-cookie": "JSESSIONID=logged-in; Path=/api"},
        )
    )
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [])

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == USER_A["email"]
    assert response.cookies.get("maint_session") == "logged-in"

    vehicles = client.get("/api/v1/vehicles")
    assert vehicles.status_code == 200


def test_login_invalid_credentials_returns_401(client, traccar_mock):
    traccar_mock.post(f"{TRACCAR}/api/session").mock(return_value=Response(401))

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


def test_valid_session_cookie_is_accepted(client, traccar_mock):
    session_route = mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [])

    client.cookies.set("JSESSIONID", "abc123")
    response = client.get("/api/v1/vehicles")

    assert response.status_code == 200
    # The cookie must be forwarded to Traccar as-is.
    forwarded = session_route.calls.last.request.headers.get("cookie", "")
    assert "JSESSIONID=abc123" in forwarded


def test_bearer_token_is_accepted_and_forwarded(client, traccar_mock):
    session_route = mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [])

    response = client.get(
        "/api/v1/vehicles", headers={"Authorization": "Bearer my-api-token"}
    )

    assert response.status_code == 200
    forwarded = session_route.calls.last.request.headers.get("authorization")
    assert forwarded == "Bearer my-api-token"


def test_rejected_traccar_session_returns_401(client, traccar_mock):
    mock_session(traccar_mock, None)

    client.cookies.set("JSESSIONID", "expired")
    response = client.get("/api/v1/vehicles")

    assert response.status_code == 401


def test_session_validation_is_cached(client, traccar_mock):
    session_route = mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [])

    client.cookies.set("JSESSIONID", "abc123")
    for _ in range(3):
        assert client.get("/api/v1/vehicles").status_code == 200

    # Session validated against Traccar exactly once thanks to the 60s cache.
    assert session_route.call_count == 1


def test_different_credentials_are_cached_separately(client, traccar_mock):
    session_route = mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [])

    client.cookies.set("JSESSIONID", "cookie-one")
    client.get("/api/v1/vehicles")
    client.cookies.set("JSESSIONID", "cookie-two")
    client.get("/api/v1/vehicles")

    assert session_route.call_count == 2


def test_traccar_5xx_maps_to_502(client, traccar_mock):
    traccar_mock.get(f"{TRACCAR}/api/session").mock(return_value=Response(500))

    client.cookies.set("JSESSIONID", "abc123")
    response = client.get("/api/v1/vehicles")

    assert response.status_code == 502


def test_traccar_down_maps_to_502(client, traccar_mock):
    import httpx

    traccar_mock.get(f"{TRACCAR}/api/session").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    client.cookies.set("JSESSIONID", "abc123")
    response = client.get("/api/v1/vehicles")

    assert response.status_code == 502
