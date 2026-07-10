from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # Traccar's login field is named "email" but accepts the account login name.
    email: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    administrator: bool
    readonly: bool = False
    device_readonly: bool = False
