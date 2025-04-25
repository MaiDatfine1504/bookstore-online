import json, os, hashlib
from datetime import datetime
from app import app, db
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from enum import Enum as RoleEnum
from flask_login import UserMixin
class UserEnum(RoleEnum):
    USER = 1
    ADMIN = 2
    MANAGER = 3
    EMPLOYEE = 4
class PaymentMethodEnum(RoleEnum):
    ONLINE = 'online'
    OFFLINE = 'offline'

class OrderStatusEnum(RoleEnum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELED = 'canceled'
class Base(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_date = Column(DateTime, default=datetime.now())
    active = Column(Boolean, default=True)

    def __str__(self):
        return self.name
class Rule(Base):
    min_import = Column(Integer, nullable=False, default=150)
    min_stock = Column(Integer, nullable=False, default=300)
    cancel_time = Column(Integer, nullable=False, default=48)
class User(Base, UserMixin):
    name = Column(String(100))
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(50), nullable=False)
    role = Column(Enum(UserEnum), default=UserEnum.USER)
    receipts = relationship('Receipt', backref="user", lazy=True)
    address = relationship('Address', backref='user', uselist=False, cascade="all, delete-orphan")
class Genre(Base):
    name = Column(String(50), nullable=False, unique=True)
    books = relationship('Book', backref="genre", lazy=True)
class Book(Base):
    title = Column(String(100), nullable=False)
    image = Column(String(300), default="...")
    genre_id = Column(Integer, ForeignKey(Genre.id), nullable=False)
    author = Column(String(50), nullable=False)
    price = Column(Float, default=0)
    quantity = Column(Integer, default=0)
    details = relationship('ReceiptDetail', backref='book', lazy=True)
class Receipt(Base):
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    total_price = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethodEnum), default=PaymentMethodEnum.OFFLINE)
    status = Column(Enum(OrderStatusEnum), default=OrderStatusEnum.PENDING)
    details = relationship('ReceiptDetail', backref='receipt', lazy=True)
class ReceiptDetail(Base):
    quantity = Column(Integer, default=0)
    unit_price = Column(Float, default=0)
    receipt_id = Column(Integer, ForeignKey(Receipt.id), nullable=False)
    book_id = Column(Integer, ForeignKey(Book.id), nullable=False)

class Address(Base):
    house_number = Column(String(50))       
    street = Column(String(100))            
    ward = Column(String(100))              
    district = Column(String(100))          
    city = Column(String(100))              
    country = Column(String(100))           
    user_id = Column(Integer, ForeignKey(User.id), unique=True, nullable=False)

# -------------------------
# Khởi tạo cơ sở dữ liệu và dữ liệu mẫu
# -------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
        basedir = os.path.dirname(os.path.abspath(__file__))
        file_path_genres = os.path.join(basedir, "app/data", "genres.json")
        file_path_books = os.path.join(basedir, "app/data", "books.json")

        # Thêm thể loại
        with open(file_path_genres, encoding='utf-8') as f:
            genres = json.load(f)
            for genre in genres:
                g = Genre(id=genre['id'], name=genre['name'])
                db.session.add(g)

        # Thêm sách
        with open(file_path_books, encoding='utf-8') as f:
            books = json.load(f)
            for book in books:
                b = Book(
                    id=book['id'],
                    title=book['title'],
                    image=book['image'],
                    price=book['price'],
                    quantity=book['quantity'],
                    genre_id=book['genre_id'],
                    author=book['author']
                )
                db.session.add(b)

        # Địa chỉ người dùng
        address1 = Address(
            house_number="110", street="TX14", ward="Thạnh Xuân", 
            district="Quận 12", city="Ho Chi Minh city", 
            country="Vietnam"
        )

        # Người dùng
        u1 = User(
            name="Người dùng thường 1", username="user1",
            password=hashlib.md5("user1123".encode()).hexdigest(),
            role=UserEnum.USER, address=address1
        )

        u2 = User(
            name="Người dùng thường 2", username="user2",
            password=hashlib.md5("user2123".encode()).hexdigest(),
            role=UserEnum.USER
        )

        u3 = User(
            name="Quản trị viên", username="admin",
            password=hashlib.md5("admin123".encode()).hexdigest(),
            role=UserEnum.ADMIN
        )

        u4 = User(
            name="Quản lý", username="manager",
            password=hashlib.md5("manager123".encode()).hexdigest(),
            role=UserEnum.MANAGER
        )

        u5 = User(
            name="Nhân viên", username="employee",
            password=hashlib.md5("employee123".encode()).hexdigest(),
            role=UserEnum.EMPLOYEE
        )
        db.session.add_all([u1, u2, u3, u4, u5])

        rule = Rule(min_import=150, min_stock=300, cancel_time=48)
        db.session.add(rule)
        db.session.commit()