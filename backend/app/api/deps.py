"""Authentication & authorization dependencies.

No local user accounts: we piggyback on Traccar sessions. The incoming
JSESSIONID cookie or Bearer token is forwarded to Traccar's /api/session;
a 200 means the caller is a valid Traccar user. Device-level authorization
asks Traccar (with the caller's own credentials) whether the device is
visible to them — so tenant isolation is exactly Traccar's.
"""

import time
from dataclasses import dataclass
from typing import Annotated, Any, Hashable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Vehicle
from app.services.traccar import TraccarService, UserCredential, get_traccar
from app.services.tenant_scope import resolve_tenant_user_id

SESSION_CACHE_TTL_SECONDS = 60.0
DEVICE_CACHE_TTL_SECONDS = 300.0
SESSION_COOKIE_NAME = "maint_session"


@dataclass(frozen=True)
class TraccarUser:
    id: int
    name: str
    email: str
    administrator: bool
    user_limit: int
    readonly: bool
    device_readonly: bool


def traccar_writes_disabled(user: TraccarUser) -> bool:
    """True when Traccar blocks this user from editing devices or schedules."""
    return user.readonly or user.device_readonly


def require_traccar_write_access(ctx: "AuthContext") -> None:
    """Raise 403 when the caller's Traccar account is read-only."""
    if traccar_writes_disabled(ctx.user):
        from app.services.traccar import TRACCAR_NO_PERMISSION_DETAIL

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=TRACCAR_NO_PERMISSION_DETAIL,
        )


@dataclass(frozen=True)
class AuthContext:
    user: TraccarUser
    credential: UserCredential
    tenant_user_id: int | None


class TTLCache:
    """Minimal in-memory TTL cache. Single-process app (see Dockerfile), so this is safe."""

    def __init__(self, ttl_seconds: float, max_entries: int = 10_000) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._data: dict[Hashable, tuple[float, Any]] = {}

    def get(self, key: Hashable) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: Hashable, value: Any) -> None:
        if len(self._data) >= self._max_entries:
            now = time.monotonic()
            self._data = {k: v for k, v in self._data.items() if v[0] > now}
            if len(self._data) >= self._max_entries:
                self._data.clear()
        self._data[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        self._data.clear()


_session_cache = TTLCache(SESSION_CACHE_TTL_SECONDS)
_device_cache = TTLCache(DEVICE_CACHE_TTL_SECONDS)


def clear_auth_caches() -> None:
    """Used by tests."""
    _session_cache.clear()
    _device_cache.clear()


def _extract_credential(request: Request) -> UserCredential | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            return UserCredential(bearer_token=token)
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME) or request.cookies.get(
        "JSESSIONID"
    )
    if session_cookie:
        return UserCredential(session_cookie=session_cookie)
    return None


async def get_current_user(
    request: Request,
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> AuthContext:
    credential = _extract_credential(request)
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Log in with your Traccar email and password.",
        )

    cache_key = credential.cache_key()
    cached = _session_cache.get(cache_key)
    if cached is not None:
        return cached

    session = await traccar.as_user(credential).get_session()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Traccar session",
        )

    user = TraccarUser(
        id=session["id"],
        name=session.get("name", ""),
        email=session.get("email", ""),
        administrator=bool(session.get("administrator", False)),
        user_limit=int(session.get("userLimit", 0)),
        readonly=bool(session.get("readonly", False)),
        device_readonly=bool(session.get("deviceReadonly", False)),
    )
    tenant_user_id = await resolve_tenant_user_id(
        traccar,
        credential,
        user_id=user.id,
        administrator=user.administrator,
        user_limit=user.user_limit,
    )
    ctx = AuthContext(user=user, credential=credential, tenant_user_id=tenant_user_id)
    _session_cache.set(cache_key, ctx)
    return ctx


CurrentUser = Annotated[AuthContext, Depends(get_current_user)]


async def verify_device_access(
    ctx: AuthContext,
    traccar: TraccarService,
    traccar_device_id: int,
) -> None:
    """Raise 404 unless the current user can see this Traccar device.

    Uses the caller's OWN credentials — never the admin token — so tenant
    isolation is exactly Traccar's. Responds 404 (not 403) to avoid revealing
    that a device exists at all.
    """
    cache_key = (ctx.user.id, traccar_device_id)
    if _device_cache.get(cache_key):
        return

    device = await traccar.as_user(ctx.credential).get_device(traccar_device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )
    _device_cache.set(cache_key, True)


async def get_authorized_vehicle(
    vehicle_id: int,
    ctx: CurrentUser,
    db: Annotated["Session", Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> "Vehicle":
    """Load a local vehicle row and enforce Traccar device visibility.

    404 both when the row doesn't exist and when the user may not see the
    device, so existence is never revealed across tenants.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    await verify_device_access(ctx, traccar, vehicle.traccar_device_id)
    return vehicle


AuthorizedVehicle = Annotated["Vehicle", Depends(get_authorized_vehicle)]
