from pydantic import BaseModel, ConfigDict, Field, computed_field


class ServiceTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    default_interval_km: int | None = Field(default=None, gt=0)
    default_interval_days: int | None = Field(default=None, gt=0)


class ServiceTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    default_interval_km: int | None = Field(default=None, gt=0)
    default_interval_days: int | None = Field(default=None, gt=0)


class ServiceTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    traccar_maintenance_type: str | None = None
    default_interval_km: int | None
    default_interval_days: int | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_name(self) -> str:
        return self.name
