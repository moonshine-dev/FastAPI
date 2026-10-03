from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, le=1_000_000)
    stock: int = Field(ge=0, le=1_000_000)
    description: Optional[str] = Field(default=None, max_length=500)


class BookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    description: Optional[str] = Field(default=None, max_length=500)
