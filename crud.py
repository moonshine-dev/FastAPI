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

def get_books(db: Session):
    return db.query(models.Book).all()

def get_book_by_id(db: Session, book_id: int):
    return db.query(models.Book).filter(models.Book.id == book_id).first()


def create_order(db: Session, order: schemas.OrderCreate):
    book = get_book_by_id(db, book_id=order.book_id)
    
    if book is None or book.stock <= 0:
        return None
        
    book.stock -= 1
    
    new_order = models.Order(
        user_id=order.user_id,
        book_id=order.book_id,
        return_deadline=order.return_deadline
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

def return_book(db: Session, order_id: int):
    
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    
    #meaning if the boook was not returned
    if order and order.delivery_date is None:

        order.delivery_date = datetime.now(timezone.utc)
        
        book = get_book_by_id(db, book_id=order.book_id)
        if book:
            book.stock += 1
            
        db.commit()
        db.refresh(order)
        return order
        
    return None

def get_delayed_orders(db: Session):
    now = datetime.now(timezone.utc)
    return db.query(models.Order).filter(
        models.Order.delivery_date.is_(None),
        models.Order.return_deadline < now
    ).all()