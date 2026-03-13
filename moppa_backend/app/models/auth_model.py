from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=255)


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class AuthTokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthUserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool


class AuthLoginResponse(AuthTokenPairResponse):
    user: AuthUserResponse
