from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(ge=1)
    book_id: int = Field(ge=1)
    return_deadline: datetime

    @model_validator(mode="after")
    def deadline_must_be_future(self) -> "OrderCreate":
        deadline = self.return_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= datetime.now(timezone.utc):
            raise ValueError("return_deadline must be in the future")
        return self


class OrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int = Field(ge=1)
    user_id: int = Field(ge=1)
    book_id: int = Field(ge=1)
    order_date: datetime
    return_deadline: datetime
    delivery_date: Optional[datetime] = None
