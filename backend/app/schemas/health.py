from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: bool
    traccar_reachable: bool
    traccar_public_url: str | None = None


class AppConfigResponse(BaseModel):
    traccar_public_url: str | None = None
