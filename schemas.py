from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BookCreate(BaseModel):
    title: str
    author: str
    price: float
    stock: int
    description: Optional[str] = None 

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    price: float
    stock: int
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    user_id: int
    book_id: int
    return_deadline: datetime

class OrderResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    order_date: datetime
    return_deadline: datetime
    delivery_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
