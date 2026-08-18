from database import engine, Base
from models import User, Book, Order


Base.metadata.create_all(bind=engine)

print("Tables created successfully!")

