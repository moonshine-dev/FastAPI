from sqlalchemy.orm import Session
from datetime import datetime, timezone
from passlib.context import CryptContext
import models, schemas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
# to return some gibberish password
    return pwd_context.hash(password)



def create_user(db: Session, user: schemas.UserCreate):

    hashed_pwd = get_password_hash(user.password)
    
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pwd
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_book(db: Session, book: schemas.BookCreate):
    new_book = models.Book(
        title=book.title,
        author=book.author,
        price=book.price,
        stock=book.stock,
        description=book.description
    )
    
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

def get_books(db: Session, skip: int = 0, limit: int = 10):
    query = db.query(models.Book)
    total = query.count()
    books = query.order_by(models.Book.id).offset(skip).limit(limit).all()
    return books, total

def get_book_by_id(db: Session, book_id: int):
    return db.query(models.Book).filter(models.Book.id == book_id).first()

def search_books_by_title(db: Session, title: str, skip: int = 0, limit: int = 10):
    query = db.query(models.Book).filter(models.Book.title == title)
    total = query.count()
    books = query.order_by(models.Book.id).offset(skip).limit(limit).all()
    return books, total


def create_order(db: Session, order: schemas.OrderCreate):
    rows = db.query(models.Book).filter(
        models.Book.id == order.book_id,
        models.Book.stock > 0
    ).update(
        {"stock": models.Book.stock - 1},
        synchronize_session=False
    )

    if rows == 0:
        db.rollback()
        return None

    new_order = models.Order(
        user_id=order.user_id,
        book_id=order.book_id,
        return_deadline=order.return_deadline
    )

    try:
        db.add(new_order)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(new_order)
    return new_order

def return_book(db: Session, order_id: int):
    rows = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.delivery_date.is_(None)
    ).update(
        {"delivery_date": datetime.now(timezone.utc)},
        synchronize_session=False
    )

    if rows == 0:
        db.rollback()
        return None

    book_id = db.query(models.Order.book_id).filter(
        models.Order.id == order_id
    ).scalar()

    db.query(models.Book).filter(
        models.Book.id == book_id
    ).update(
        {"stock": models.Book.stock + 1},
        synchronize_session=False
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_delayed_orders(db: Session, skip: int = 0, limit: int = 10):
    now = datetime.now(timezone.utc)
    query = db.query(models.Order).filter(
        models.Order.delivery_date.is_(None),
        models.Order.return_deadline < now
    )
    total = query.count()
    orders = query.order_by(models.Order.id).offset(skip).limit(limit).all()
    return orders, total