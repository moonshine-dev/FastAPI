from fastapi import FastAPI

from database import Base, engine
from app.books.router import router as books_router
from app.orders.router import router as orders_router
from app.users.router import router as users_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Library Management System", version="1.0.0")

app.include_router(users_router)
app.include_router(books_router)
app.include_router(orders_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Library Management System!"}
