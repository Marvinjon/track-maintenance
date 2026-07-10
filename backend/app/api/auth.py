"""Login/logout using Traccar email + password.

The maintenance app runs on its own domain, so we cannot rely on Traccar's
JSESSIONID cookie being sent by the browser. After a successful Traccar login
we store the session id in our own HttpOnly cookie (``maint_session``).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status

from app.api.deps import (
    SESSION_COOKIE_NAME,
    AuthContext,
    CurrentUser,
    _extract_credential,
    clear_auth_caches,
    traccar_writes_disabled,
)
from app.config import Settings, get_settings
from app.schemas.auth import LoginRequest, UserResponse
from app.services.traccar import TraccarService, TraccarUnavailable, UserCredential, get_traccar
from app.services.user_sync import clear_user_sync_throttle, schedule_user_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_cookie_kwargs(settings: Settings) -> dict:
    return {
        "httponly": True,
        "secure": settings.session_cookie_secure,
        "samesite": "lax",
        "path": "/",
    }


def _user_response(user: AuthContext) -> UserResponse:
    return UserResponse(
        id=user.user.id,
        name=user.user.name,
        email=user.user.email,
        administrator=user.user.administrator,
        readonly=user.user.readonly,
        device_readonly=user.user.device_readonly,
    )


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    traccar: Annotated[TraccarService, Depends(get_traccar)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    try:
        result = await traccar.login(payload.email, payload.password)
    except TraccarUnavailable as exc:
        logger.error("Traccar unavailable during login: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Traccar is unavailable right now, please try again shortly.",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user, session_id = result
    clear_auth_caches()
    clear_user_sync_throttle()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        **_session_cookie_kwargs(settings),
    )
    schedule_user_sync(
        background_tasks,
        traccar_user_id=int(user["id"]),
        credential=UserCredential(session_cookie=session_id),
        force=True,
        prune_missing_maintenance=not (
            bool(user.get("readonly", False)) or bool(user.get("deviceReadonly", False))
        ),
    )
    return UserResponse(
        id=user["id"],
        name=user.get("name", ""),
        email=user.get("email", ""),
        administrator=bool(user.get("administrator", False)),
        readonly=bool(user.get("readonly", False)),
        device_readonly=bool(user.get("deviceReadonly", False)),
    )


@router.get("/me", response_model=UserResponse)
async def me(
    ctx: CurrentUser,
    background_tasks: BackgroundTasks,
) -> UserResponse:
    schedule_user_sync(
        background_tasks,
        traccar_user_id=ctx.user.id,
        credential=ctx.credential,
        prune_missing_maintenance=not traccar_writes_disabled(ctx.user),
    )
    return _user_response(ctx)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    traccar: Annotated[TraccarService, Depends(get_traccar)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    credential = _extract_credential(request)
    if credential is not None and credential.session_cookie:
        try:
            await traccar.as_user(credential).logout()
        except TraccarUnavailable:
            logger.warning("Traccar unavailable during logout; clearing local session")

    clear_auth_caches()
    clear_user_sync_throttle()
    response.delete_cookie(SESSION_COOKIE_NAME, **_session_cookie_kwargs(settings))
    return response
