import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.orders.schemas import OrderResponse

USERNAME_PATTERN = r"^[a-zA-Z0-9_.-]{3,50}$"


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(pattern=USERNAME_PATTERN, description="3-50 chars: letters, digits, _ . -")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def username_not_reserved(cls, value: str) -> str:
        if value.lower() in {"admin", "root", "system"}:
            raise ValueError("username is reserved")
        return value

    @field_validator("password")
    @classmethod
    def password_needs_letter_and_digit(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("password must contain at least one letter and one digit")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int = Field(ge=1)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    is_active: bool


class UserWithOrders(UserResponse):
    orders: list[OrderResponse] = Field(default_factory=list)
