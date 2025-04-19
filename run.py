from flask import render_template, abort, request, redirect, url_for, flash, jsonify
from flask_login import login_user
from sqlalchemy.orm import joinedload
from app import app, db, login
from app.models import Book, Genre, User, UserEnum
import hashlib

@app.context_processor
def common_data():
    return {
        'genres': Genre.query.all()
    }

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = hashlib.md5(request.form.get("password").encode('utf-8')).hexdigest()

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)

            # Chuyển hướng theo vai trò
            if user.role == UserEnum.ADMIN:
                return redirect(url_for('admin_dashboard'))
            elif user.role == UserEnum.MANAGER:
                return redirect(url_for('manager_dashboard'))
            elif user.role == UserEnum.EMPLOYEE:
                return redirect(url_for('employee_dashboard'))
            else:
                return redirect(url_for('homepage'))
        else:
            flash("Sai thông tin đăng nhập!", "danger")
    return render_template("login.html")

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('dashboard/admin.html')

@app.route('/manager/dashboard')
def manager_dashboard():
    return render_template('dashboard/manager.html')

# Lấy danh sách sách từ cơ sở dữ liệu
@app.route('/api/books', methods=['GET'])
def get_books():
    books = Book.query.all()
    return jsonify([{
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'image': book.image,
        'quantity': book.quantity,
        'genre': book.genre.name
    } for book in books])

# Cập nhật thông tin sách
@app.route('/api/books/<int:id>', methods=['PUT'])
def update_book(id):
    book = Book.query.get_or_404(id)
    data = request.json
    book.title = data.get('title', book.title)
    book.author = data.get('author', book.author)
    book.image = data.get('author', book.image)
    book.quantity = data.get('quantity', book.quantity)
    book.genre_id = data.get('genre_id', book.genre_id)
    db.session.commit()
    return jsonify({
        'message': 'Book updated successfully',
        'book': {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'image': book.image,
            'quantity': book.quantity,
            'genre': book.genre.name
        }
    })

# Xoá sách
@app.route('/api/books/<int:id>', methods=['DELETE'])
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    return jsonify({'message': 'Book deleted successfully'})

#Tìm kiếm sách
@app.route('/api/books/search')
def search_books():
    keyword = request.args.get('q', '').strip().lower()
    if not keyword:
        return jsonify([])

    books = Book.query.join(Genre).options(joinedload(Book.genre)).filter(
        Book.title.ilike(f"%{keyword}%") |
        Book.author.ilike(f"%{keyword}%") |
        Genre.name.ilike(f"%{keyword}%")
    ).all()

    return jsonify([
        {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'image': book.image,
            'quantity': book.quantity,
            'genre': book.genre.name
        } for book in books
    ])

#Thêm sách mới
@app.route('/api/books', methods=['POST'])
def add_book():
    data = request.json
    title = data.get('title')
    author = data.get('author')
    image = data.get('image')
    genre_name = data.get('genre')
    quantity = data.get('quantity')

    if not all([title, author, image, genre_name, quantity]):
        return jsonify({'error': 'Thiếu thông tin'}), 400

    # Tìm hoặc tạo thể loại
    genre = Genre.query.filter_by(name=genre_name).first()
    if not genre:
        genre = Genre(name=genre_name)
        db.session.add(genre)
        db.session.commit()

    # Tạo sách mới
    new_book = Book(
        title=title,
        author=author,
        image=image,
        quantity=quantity,
        genre_id=genre.id
    )
    db.session.add(new_book)
    db.session.commit()

    return jsonify({'message': 'Thêm sách thành công'})

@app.route('/employee/dashboard')
def employee_dashboard():
    return render_template('dashboard/employee.html')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        password = hashlib.md5(request.form.get("password").encode("utf-8")).hexdigest()

        if User.query.filter_by(username=username).first():
            flash("Tên đăng nhập đã tồn tại!", "warning")
        else:
            new_user = User(name=name, username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash("Đăng ký thành công, bạn có thể đăng nhập!", "success")
            return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/")
def homepage():
    books = Book.query.all()
    return render_template('homepage.html', books=books)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get(book_id)
    if book is None:
        abort(404)
    return render_template('book_detail.html', book=book)

@app.route('/genre/<int:genre_id>')
def books_by_genre(genre_id):
    books = Book.query.filter_by(genre_id=genre_id).all()
    genre = Genre.query.get(genre_id)
    
    if not genre:
        abort(404)

    return render_template('homepage.html', books=books, genre=genre)

@app.route('/search')
def search():
    keyword = request.args.get('keyword', '').strip()
    books = Book.query

    if keyword:
        books = books.filter(
            (Book.title.ilike(f'%{keyword}%')) |
            (Genre.name.ilike(f'%{keyword}%'))
        ).join(Genre)

    books = books.all()

    return render_template('homepage.html', books=books)

if __name__ == "__main__":
    app.run(debug=True)