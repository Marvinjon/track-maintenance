"""Thin typed wrapper around the Traccar REST API.

``as_user(credential)`` forwards the caller's own Traccar credentials
(session cookie or bearer token). Used for session validation, device
visibility, and all Traccar data reads/writes.

All unit conversions between Traccar and this service live here:
Traccar reports totalDistance in meters and engine hours in milliseconds;
the rest of the codebase deals in km and hours exclusively.
"""

import hashlib
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings

_TIMEOUT_SECONDS = 10.0

M_PER_KM = 1000.0
MS_PER_HOUR = 3_600_000.0


class TraccarUnavailable(Exception):
    """Traccar could not be reached (connect error/timeout or 5xx)."""


class TraccarPermissionDenied(Exception):
    """Caller lacks Traccar edit permission (e.g. read-only user)."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or TRACCAR_NO_PERMISSION_DETAIL)


TRACCAR_NO_PERMISSION_DETAIL = "You do not have permission to update Traccar."


def meters_to_km(meters: float) -> float:
    return round(meters / M_PER_KM, 1)


def km_to_meters(km: float) -> float:
    return km * M_PER_KM


def ms_to_hours(ms: float) -> float:
    return round(ms / MS_PER_HOUR, 1)


def hours_to_ms(hours: float) -> float:
    return hours * MS_PER_HOUR


@dataclass(frozen=True)
class UserCredential:
    """The caller's Traccar credential: a JSESSIONID cookie value or an API token."""

    session_cookie: str | None = None
    bearer_token: str | None = None

    def cache_key(self) -> str:
        material = f"cookie:{self.session_cookie}|bearer:{self.bearer_token}"
        return hashlib.sha256(material.encode()).hexdigest()


class TraccarClient:
    """A client bound to one set of user credentials."""

    def __init__(
        self,
        base_url: str,
        *,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._cookies = cookies or {}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        last_error: Exception | None = None
        # One retry on connect-level errors only.
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    headers=self._headers,
                    cookies=self._cookies,
                    timeout=_TIMEOUT_SECONDS,
                ) as client:
                    return await client.request(method, path, params=params, json=json)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                last_error = exc
            except httpx.HTTPError as exc:
                raise TraccarUnavailable(str(exc)) from exc
        raise TraccarUnavailable(str(last_error)) from last_error

    @staticmethod
    def _check_5xx(response: httpx.Response) -> None:
        if response.status_code >= 500:
            raise TraccarUnavailable(
                f"Traccar returned {response.status_code} for {response.request.url.path}"
            )

    async def logout(self) -> None:
        response = await self._request("DELETE", "/api/session")
        self._check_5xx(response)

    async def get_session(self) -> dict[str, Any] | None:
        """Validate the bound credential. Returns the Traccar user JSON or None."""
        response = await self._request("GET", "/api/session")
        self._check_5xx(response)
        if response.status_code == 200:
            return response.json()
        return None

    async def list_devices(self) -> list[dict[str, Any]]:
        """Devices visible to the bound credential."""
        response = await self._request("GET", "/api/devices")
        self._check_5xx(response)
        if response.status_code == 200:
            return response.json()
        return []

    async def get_device(self, device_id: int) -> dict[str, Any] | None:
        """Return the device if the bound credential may see it, else None."""
        response = await self._request("GET", "/api/devices", params={"id": device_id})
        self._check_5xx(response)
        if response.status_code != 200:
            return None
        devices = response.json()
        for device in devices:
            if device.get("id") == device_id:
                return device
        return None

    async def get_latest_position(self, device_id: int) -> dict[str, Any] | None:
        """Latest known position for a device visible to the bound credential."""
        response = await self._request("GET", "/api/positions", params={"deviceId": device_id})
        self._check_5xx(response)
        if response.status_code != 200:
            return None
        positions = response.json()
        return positions[0] if positions else None

    async def ping(self) -> bool:
        """Best-effort reachability check (GET /api/server needs no auth)."""
        try:
            response = await self._request("GET", "/api/server")
            return response.status_code < 500
        except TraccarUnavailable:
            return False

    # -- Maintenance ---------------------------------------------------------
    # Traccar maintenance entities use raw units: meters for totalDistance,
    # milliseconds for hours. Callers convert via km_to_meters/hours_to_ms.

    async def list_maintenances(self, device_id: int) -> list[dict[str, Any]]:
        """Maintenance schedules linked to a device."""
        last_status: int | None = None
        for path in ("/api/maintenances", "/api/maintenance"):
            response = await self._request(
                "GET", path, params={"deviceId": device_id}
            )
            self._check_5xx(response)
            if response.status_code == 403:
                raise TraccarPermissionDenied()
            if response.status_code == 200:
                body = response.json()
                return body if isinstance(body, list) else []
            last_status = response.status_code
        if last_status is not None:
            raise TraccarUnavailable(
                f"Traccar rejected maintenance list ({last_status})"
            )
        return []

    async def create_maintenance(self, data: dict[str, Any]) -> dict[str, Any]:
        last_status: int | None = None
        for path in ("/api/maintenances", "/api/maintenance"):
            response = await self._request("POST", path, json=data)
            self._check_5xx(response)
            if response.status_code == 200:
                return response.json()
            last_status = response.status_code
        raise TraccarUnavailable(
            f"Traccar rejected maintenance creation ({last_status})"
        )

    async def update_maintenance(
        self, maintenance_id: int, data: dict[str, Any]
    ) -> dict[str, Any]:
        last_status: int | None = None
        for path in (
            f"/api/maintenances/{maintenance_id}",
            f"/api/maintenance/{maintenance_id}",
        ):
            response = await self._request("PUT", path, json=data)
            self._check_5xx(response)
            if response.status_code == 403:
                raise TraccarPermissionDenied()
            if response.status_code == 200:
                return response.json()
            last_status = response.status_code
        raise TraccarUnavailable(
            f"Traccar rejected maintenance update ({last_status})"
        )

    async def delete_maintenance(self, maintenance_id: int) -> None:
        last_status: int | None = None
        for path in (
            f"/api/maintenances/{maintenance_id}",
            f"/api/maintenance/{maintenance_id}",
        ):
            response = await self._request("DELETE", path)
            self._check_5xx(response)
            if response.status_code in (204, 404):
                return
            last_status = response.status_code
        raise TraccarUnavailable(
            f"Traccar rejected maintenance deletion ({last_status})"
        )

    # -- Permissions --------------------------------------------------------

    async def list_permissions(self, **params: int) -> list[dict[str, Any]]:
        """Fetch permission links (e.g. deviceId + notificationId=0)."""
        response = await self._request("GET", "/api/permissions", params=params)
        self._check_5xx(response)
        if response.status_code != 200:
            return []
        body = response.json()
        return body if isinstance(body, list) else []

    async def create_permission(self, data: dict[str, Any]) -> None:
        """Bind entities, e.g. {"deviceId": ..., "maintenanceId": ...}."""
        response = await self._request("POST", "/api/permissions", json=data)
        self._check_5xx(response)
        if response.status_code not in (200, 204):
            raise TraccarUnavailable(
                f"Traccar rejected permission creation ({response.status_code})"
            )

    async def update_device_accumulators(
        self,
        device_id: int,
        *,
        total_distance_m: float | None = None,
        hours_ms: float | None = None,
    ) -> None:
        """Push totalDistance (meters) and/or hours (ms) to Traccar.

        Omitted fields are left unchanged on the device. Requires a latest
        position to exist in Traccar (same constraint as the web UI).
        """
        payload: dict[str, Any] = {"deviceId": device_id}
        if total_distance_m is not None:
            payload["totalDistance"] = total_distance_m
        if hours_ms is not None:
            payload["hours"] = hours_ms
        response = await self._request(
            "PUT", f"/api/devices/{device_id}/accumulators", json=payload
        )
        self._check_5xx(response)
        if response.status_code == 403:
            raise TraccarPermissionDenied()
        if response.status_code not in (200, 204):
            raise TraccarUnavailable(
                f"Traccar rejected accumulator update ({response.status_code})"
            )


class TraccarService:
    """Factory producing credential-bound clients."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def as_user(self, credential: UserCredential) -> TraccarClient:
        headers: dict[str, str] = {}
        cookies: dict[str, str] = {}
        if credential.bearer_token:
            headers["Authorization"] = f"Bearer {credential.bearer_token}"
        elif credential.session_cookie:
            cookies["JSESSIONID"] = credential.session_cookie
        return TraccarClient(self._base_url, headers=headers, cookies=cookies)

    async def ping(self) -> bool:
        """Reachability check (GET /api/server needs no auth)."""
        return await TraccarClient(self._base_url).ping()

    async def login(self, email: str, password: str) -> tuple[dict[str, Any], str] | None:
        """Authenticate with Traccar email/password. Returns user JSON and JSESSIONID."""
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=_TIMEOUT_SECONDS,
                ) as client:
                    response = await client.post(
                        "/api/session",
                        data={"email": email, "password": password},
                    )
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                last_error = exc
                continue
            except httpx.HTTPError as exc:
                raise TraccarUnavailable(str(exc)) from exc

            if response.status_code >= 500:
                raise TraccarUnavailable(
                    f"Traccar returned {response.status_code} for /api/session"
                )
            if response.status_code != 200:
                return None

            session_id = response.cookies.get("JSESSIONID")
            if not session_id:
                return None
            return response.json(), session_id

        raise TraccarUnavailable(str(last_error)) from last_error


def get_traccar() -> TraccarService:
    settings = get_settings()
    return TraccarService(settings.traccar_url)
