"""Traccar manager-based tenant scope for shared catalog data.

Device-linked data (vehicles, records, reminders) stays scoped via Traccar
device visibility. Service types and parts are scoped by manager organization:

- Administrators see every catalog row.
- Managers (userLimit != 0) own a tenant keyed by their user id.
- Regular users inherit their manager's tenant via Traccar permissions
  (userId + managedUserId); standalone users are their own tenant.
- Rows with traccar_tenant_user_id IS NULL are global defaults (seeded types).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, or_, select, true
from sqlalchemy.orm import Session

from app.services.traccar import TraccarService, UserCredential

if TYPE_CHECKING:
    from app.api.deps import AuthContext
    from app.models import Part, ServiceType

T = TypeVar("T")


async def find_manager_user_id(
    traccar: TraccarService,
    credential: UserCredential,
    user_id: int,
) -> int | None:
    """Return the Traccar manager for a managed user, or None if standalone."""
    links = await traccar.as_user(credential).list_permissions(
        managedUserId=user_id, userId=0
    )
    for link in links:
        manager_id = link.get("userId")
        if isinstance(manager_id, int) and manager_id != user_id:
            return manager_id
    return None


async def resolve_tenant_user_id(
    traccar: TraccarService,
    credential: UserCredential,
    *,
    user_id: int,
    administrator: bool,
    user_limit: int,
) -> int | None:
    """Resolve catalog tenant for the current user.

    Returns None for administrators (unrestricted catalog access).
    """
    if administrator:
        return None
    if user_limit != 0:
        return user_id
    manager_id = await find_manager_user_id(traccar, credential, user_id)
    return manager_id if manager_id is not None else user_id


def create_tenant_id(ctx: AuthContext) -> int:
    """Tenant id to store on newly created catalog rows or vehicles."""
    if ctx.tenant_user_id is not None:
        return ctx.tenant_user_id
    return ctx.user.id


def catalog_visibility_filter(
    tenant_column: ColumnElement,
    tenant_user_id: int | None,
) -> ColumnElement:
    """SQL filter: global defaults plus rows owned by this tenant."""
    if tenant_user_id is None:
        return true()
    return or_(tenant_column.is_(None), tenant_column == tenant_user_id)


def tenant_match_filter(
    tenant_column: ColumnElement,
    tenant_id: int,
) -> ColumnElement:
    """SQL filter for rows owned by one tenant (not including global defaults)."""
    return tenant_column == tenant_id


def tenant_name_conflict_filter(
    tenant_column: ColumnElement,
    tenant_id: int,
) -> ColumnElement:
    """Names must be unique within a tenant and cannot shadow global defaults."""
    return or_(tenant_column.is_(None), tenant_column == tenant_id)


def assert_catalog_visible(
    entity: ServiceType | Part,
    tenant_user_id: int | None,
    *,
    detail: str,
) -> None:
    """Raise 404 when a catalog row exists but is outside the caller's tenant."""
    if tenant_user_id is None:
        return
    owner = entity.traccar_tenant_user_id
    if owner is not None and owner != tenant_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def get_service_type(
    db: Session,
    service_type_id: int,
    tenant_user_id: int | None,
) -> ServiceType:
    from app.models import ServiceType

    service_type = db.get(ServiceType, service_type_id)
    if service_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown service type",
        )
    assert_catalog_visible(service_type, tenant_user_id, detail="Service type not found")
    return service_type


def get_part(
    db: Session,
    part_id: int,
    tenant_user_id: int | None,
) -> Part:
    from app.models import Part

    part = db.get(Part, part_id)
    if part is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
    assert_catalog_visible(part, tenant_user_id, detail="Part not found")
    return part


def list_visible_service_types(
    db: Session,
    tenant_user_id: int | None,
) -> list[ServiceType]:
    from app.models import ServiceType

    query = select(ServiceType).order_by(ServiceType.name)
    query = query.where(
        catalog_visibility_filter(ServiceType.traccar_tenant_user_id, tenant_user_id)
    )
    return list(db.execute(query).scalars().all())


def vehicle_catalog_tenant(vehicle_traccar_tenant_user_id: int | None) -> int | None:
    """Tenant used when a vehicle creates or looks up catalog rows."""
    return vehicle_traccar_tenant_user_id
