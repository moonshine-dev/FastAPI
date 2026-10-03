import app  # noqa: F401  (registers all models on Base.metadata)
from database import engine, Base

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")
