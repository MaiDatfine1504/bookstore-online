import json, os, hashlib
from datetime import datetime
from app import app, db
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Enum, DateTime
from sqlalchemy.orm import relationship
from enum import Enum as RoleEnum
from flask_login import UserMixin


class UserEnum(RoleEnum):
    USER = 1
    ADMIN = 2
    MANAGER = 3
    EMPLOYEE = 4

class Base(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_date = Column(DateTime, default=datetime.now())
    active = Column(Boolean, default=True)

    def __str__(self):
        return self.name
    
class User(Base, UserMixin):
    __table_name__ = "users"
    name = Column(String(100))
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(50), nullable=False)
    role = Column(Enum(UserEnum), default=UserEnum.USER)
    receipts = relationship('Receipt', backref="user", lazy=True)

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
    details = relationship('ReceiptDetail', backref='receipt', lazy=True)

class ReceiptDetail(Base):
    quantity = Column(Integer, default=0)
    unit_price = Column(Float, default=0)
    receipt_id = Column(Integer, ForeignKey(Receipt.id), nullable=False)
    product_id = Column(Integer, ForeignKey(Book.id), nullable=False)

if __name__ =="__main__":
    with app.app_context():
        db.create_all()
        
        # Lấy thư mục chứa file hiện tại (models.py)
        basedir = os.path.dirname(os.path.abspath(__file__))

        # Nối đường dẫn tới file genres.json
        file_path_genres = os.path.join(basedir, "data", "genres.json")

        #Thêm dữ liệu về thể loại
        with open(file_path_genres, encoding='utf-8') as f:
            genres = json.load(f)

            for genre in genres:
                g = Genre(
                    id=genre['id'],
                    name=genre['name']
                )
                db.session.add(g)

        # Nối đường dẫn tới file genres.json
        file_path_books = os.path.join(basedir, "data", "books.json")

        #Thêm dữ liệu về sách
        with open(file_path_books, encoding='utf-8') as f:
            books = json.load(f)

            for book in books:
                p = Book(
                    id=book['id'],
                    title=book['title'],
                    image=book['image'],
                    price=book['price'],
                    quantity=book['quantity'],
                    genre_id=book['genre_id'],
                    author=book['author']
                )
                db.session.add(p)
        
        #Thêm dữ liệu người dùng
        u1 = User(name="Người dùng thường", username="user", 
                  password=hashlib.md5("user123".encode()).hexdigest(),
                  role=UserEnum.USER)

        u2 = User(name="Quản trị viên", username="admin", 
                  password=hashlib.md5("admin123".encode()).hexdigest(),
                  role=UserEnum.ADMIN)

        u3 = User(name="Quản lý", username="manager", 
                  password=hashlib.md5("manager123".encode()).hexdigest(),
                  role=UserEnum.MANAGER)

        u4 = User(name="Nhân viên", username="employee", 
                  password=hashlib.md5("employee123".encode()).hexdigest(),
                  role=UserEnum.EMPLOYEE)

        db.session.add_all([u1, u2, u3, u4])
        db.session.commit()