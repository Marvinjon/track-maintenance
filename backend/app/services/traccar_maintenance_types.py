"""Traccar maintenance metric types and human-readable labels.

Types and units follow Traccar (see traccar-web MaintenancePage and
MaintenanceEventHandler). Distance types use meters; hour types use milliseconds.
"""

from __future__ import annotations

# Traccar stores distance-based maintenance start/period in meters.
DISTANCE_MAINTENANCE_TYPES = frozenset(
    {
        "totalDistance",
        "odometer",
        "serviceOdometer",
        "tripOdometer",
        "obdOdometer",
        "distance",
    }
)

# Engine-hour metrics use milliseconds in the Traccar API.
HOURS_MAINTENANCE_TYPES = frozenset({"hours", "drivingTime"})

SUPPORTED_MAINTENANCE_TYPES = DISTANCE_MAINTENANCE_TYPES | HOURS_MAINTENANCE_TYPES

# Labels aligned with Traccar position attribute names (traccar-web).
MAINTENANCE_TYPE_LABELS: dict[str, str] = {
    "totalDistance": "Total distance",
    "odometer": "Odometer",
    "serviceOdometer": "Service odometer",
    "tripOdometer": "Trip odometer",
    "obdOdometer": "OBD odometer",
    "distance": "Distance",
    "hours": "Engine hours",
    "drivingTime": "Driving time",
}


def is_supported_maintenance_type(maintenance_type: str | None) -> bool:
    return maintenance_type in SUPPORTED_MAINTENANCE_TYPES


def maintenance_type_label(maintenance_type: str) -> str:
    return MAINTENANCE_TYPE_LABELS.get(maintenance_type, maintenance_type)


def service_type_display_name(
    name: str, traccar_maintenance_type: str | None
) -> str:
    if traccar_maintenance_type:
        return maintenance_type_label(traccar_maintenance_type)
    return name
