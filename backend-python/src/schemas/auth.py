from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    password_confirmation: Optional[str] = None
    timezone: Optional[str] = "America/Sao_Paulo"
    device_name: Optional[str] = "webapp"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False
    device_name: Optional[str] = "webapp"


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    agent_enabled: Optional[bool] = None
    settings: Optional[dict[str, Any]] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    timezone: str
    locale: str
    agent_enabled: bool
    is_admin: bool
    is_ai_active: bool
    monthly_token_limit: int
    tokens_used_this_month: int
    settings: Optional[dict[str, Any]] = None
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserResourceWrapper(BaseModel):
    data: UserResponse


class AuthResponse(BaseModel):
    user: UserResponse
    token: Optional[str] = None
    token_type: Optional[str] = "Bearer"
