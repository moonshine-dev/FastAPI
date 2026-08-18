from fastapi import FastAPI
from database import engine, Base
from routers import users, books, orders

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Library Management System")

app.include_router(users.router)
app.include_router(books.router)
app.include_router(orders.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Library Management System!"}