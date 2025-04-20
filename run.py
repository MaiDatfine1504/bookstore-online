from flask import render_template, abort, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import extract, func
from sqlalchemy.orm import joinedload
from app import app, db, login
from app.models import Book, Genre, User, UserEnum, Rule, Receipt, ReceiptDetail, Address
import hashlib

@app.context_processor
def common_data():
    return {
        'genres': Genre.query.all()
    }

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Điều hướng form đăng nhập
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
            else:
                return redirect(url_for('homepage'))
        else:
            flash("Sai thông tin đăng nhập!", "danger")
    return render_template("login.html")

#Điều hướng tới form đăng ký tài khoản
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

#Đăng xuất
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Bạn đã đăng xuất thành công!", "info")
    return redirect(url_for("login"))  # Hoặc chuyển về homepage nếu bạn thích

#Điều hướng tới form admin
@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('dashboard/admin.html')

#Cập nhật quy định
@app.route('/update-rule', methods=['POST'])
def update_rule():
    data = request.json
    rule = Rule.query.first()
    if not rule:
        rule = Rule()

    rule.min_import = data.get("min_import", rule.min_import)
    rule.min_stock = data.get("min_stock", rule.min_stock)
    rule.cancel_time = data.get("cancel_time", rule.cancel_time)

    db.session.add(rule)
    db.session.commit()
    return jsonify({"message": "Quy định đã được cập nhật"}), 200

#Lấy quy định
@app.route("/api/rule")
def get_rule():
    rule = Rule.query.first()
    if not rule:
        return jsonify({"error": "Chưa có quy định hệ thống"}), 400
    return jsonify({
        "min_import": rule.min_import,
        "min_stock": rule.min_stock,
        "cancel_time": rule.cancel_time
    })

#Lấy thời gian để thống kê
@app.route('/revenue-stats/times')
def get_available_months():
    from sqlalchemy import extract
    months = db.session.query(
        extract('month', Receipt.created_date).label('month'),
        extract('year', Receipt.created_date).label('year')
    ).distinct().all()
    result = [{'month': int(m), 'year': int(y)} for m, y in months]
    return jsonify({'times': result})

#Thống kê doanh thu
@app.route('/revenue-stats')
def get_revenue_stats():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    receipts = Receipt.query.filter(
        db.extract('month', Receipt.created_date) == month,
        db.extract('year', Receipt.created_date) == year
    ).all()

    category_revenue = {}
    book_freq = {}

    for receipt in receipts:
        for detail in receipt.details:
            book = detail.book
            genre_name = book.genre.name
            amount = detail.unit_price * detail.quantity

            category_revenue[genre_name] = category_revenue.get(genre_name, 0) + amount
            book_freq[book.title] = book_freq.get(book.title, 0) + detail.quantity

    return jsonify({
        'categories': list(category_revenue.items()),
        'books': list(book_freq.items())
    })

@app.route('/revenue-stats/book')
def get_book_quantity_sold():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    # Lọc các phiếu mua trong tháng/năm tương ứng
    receipts = Receipt.query.filter(
        db.extract('month', Receipt.created_date) == month,
        db.extract('year', Receipt.created_date) == year
    ).all()

    book_sales = {}
    
    # Duyệt qua các chi tiết hóa đơn và cộng dồn số lượng từng sách bán ra
    for receipt in receipts:
        for detail in receipt.details:
            book_title = detail.book.title
            if book_title in book_sales:
                book_sales[book_title] += detail.quantity
            else:
                book_sales[book_title] = detail.quantity

    # Chuyển đổi dictionary thành list các book và số lượng tương ứng
    books = [{"title": title, "quantity": quantity} for title, quantity in book_sales.items()]

    return jsonify(books)

@app.route('/books')
def get_books_admin():
    books = Book.query.all()
    return jsonify({
        'books': [{'id': book.id, 'title': book.title} for book in books]
    })

#Điều hướng tới form quản lý
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
        'price': book.price,
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
    book.image = data.get('image', book.image)
    book.price = data.get('price', book.price)
    book.quantity = data.get('quantity', book.quantity)
    genre_name = data.get('genre')
    if genre_name:
        genre = Genre.query.filter_by(name=genre_name).first()
        if genre:
            book.genre_id = genre.id
        else:
            # Nếu thể loại chưa tồn tại, tạo mới
            new_genre = Genre(name=genre_name)
            db.session.add(new_genre)
            db.session.flush()  # Để lấy được new_genre.id trước khi commit
            book.genre_id = new_genre.id
    db.session.commit()
    return jsonify({
        'message': 'Book updated successfully',
        'book': {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'image': book.image,
            'price': book.price,
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
            'price': book.price,
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
    price = data.get('price')
    genre_name = data.get('genre')
    quantity = data.get('quantity')

    if not all([title, author, image, price, genre_name, quantity]):
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
        price=price,
        quantity=quantity,
        genre_id=genre.id
    )
    db.session.add(new_book)
    db.session.commit()

    return jsonify({'message': 'Thêm sách thành công'})

#Nhập sách vào kho
@app.route("/api/add-books", methods=["POST"])
def add_books():
    data = request.get_json()
    books = data.get("books", [])
    rule = Rule.query.first()

    if not rule:
        return jsonify({"error": "Chưa có quy định hệ thống"}), 400

    for item in books:
        title = item.get("title")
        author = item.get("author")
        genre_name = item.get("genre_name")
        quantity = item.get("quantity", 0)

        if not title or not author or not genre_name:
            return jsonify({"error": "Thiếu thông tin sách."}), 400

        if quantity < rule.min_import:
            return jsonify({"error": f"Số lượng của sách '{title}' phải từ {rule.min_import} trở lên."}), 400

        book = Book.query.filter_by(title=title, author=author).first()
        if book and book.quantity >= rule.min_stock:
            return jsonify({"error": f"Không thể nhập '{title}' vì số lượng trong kho ≥ {rule.min_stock}."}), 400

        if book:
            book.quantity += quantity
        else:
            genre = Genre.query.filter_by(name=genre_name).first()
            if not genre:
                genre = Genre(name=genre_name)
                db.session.add(genre)
                db.session.flush()  # cần để lấy genre.id

            new_book = Book(
                title=title,
                author=author,
                quantity=quantity,
                genre_id=genre.id
            )
            db.session.add(new_book)

    db.session.commit()
    return jsonify({"message": "Nhập sách thành công"}), 200

#Điều hướng tới trang chủ
@app.route("/")
def homepage():
    books = Book.query.all()
    return render_template('homepage.html', books=books)

#Điều hướng tới trang thông tin sách
@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get(book_id)
    if book is None:
        abort(404)
    return render_template('book_detail.html', book=book)

#Hiển thị toàn bộ sách cùng thể loại
@app.route('/genre/<int:genre_id>')
def books_by_genre(genre_id):
    books = Book.query.filter_by(genre_id=genre_id).all()
    genre = Genre.query.get(genre_id)
    
    if not genre:
        abort(404)

    return render_template('homepage.html', books=books, genre=genre)

#Hiển thị sách/thể loại đang tìm kiếm
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

#Thêm sách vào giỏ hàng
@app.route('/add-to-cart/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    if current_user.role != UserEnum.USER:
        flash("Chỉ người dùng mới có thể thêm vào giỏ hàng.", "warning")
        return redirect(url_for('homepage'))

    quantity = request.form.get('quantity', 1, type=int)
    book = Book.query.get_or_404(book_id)

    cart_key = f'cart_{current_user.id}'
    cart = session.get(cart_key, [])

    book_in_cart = next((item for item in cart if item['id'] == book.id), None)

    if book_in_cart:
        book_in_cart['quantity'] += quantity
    else:
        cart.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'price': book.price,
            'quantity': quantity,
            'image': book.image
        })

    session[cart_key] = cart
    session.modified = True
    flash('Sách đã được thêm vào giỏ hàng!', 'success')
    return redirect(url_for('book_detail', book_id=book.id))

# Xem giỏ hàng
@app.route('/cart')
@login_required
def view_cart():
    if current_user.role != UserEnum.USER:
        flash("Chỉ người dùng mới được xem giỏ hàng.", "warning")
        return redirect(url_for('homepage'))

    cart_key = f'cart_{current_user.id}'
    cart = session.get(cart_key, [])
    return redirect(url_for('checkout', tab='cart'))


# Trang thanh toán
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    tab = request.args.get('tab', 'cart')
    cart_key = f'cart_{current_user.id}'
    cart = session.get(cart_key, [])

    # Nếu POST: xử lý lựa chọn phương thức thanh toán
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        session['payment_method'] = payment_method

        # Nếu chọn online => chuyển tab nhập địa chỉ
        if payment_method == 'online':
            return redirect(url_for('checkout', tab='address'))
        else:
            # Nếu offline => chuyển sang finalize_order để tạo hóa đơn luôn
            return redirect(url_for('finalize_order'))

    # Nếu là GET: hiển thị trang theo tab đang chọn
    receipt = None
    receipt_id = request.args.get('receipt_id')
    if tab == 'result' and receipt_id:
        receipt = Receipt.query.get(receipt_id)

    address = current_user.address if tab in ['address', 'result'] else None
    payment_method = session.get('payment_method') or request.args.get('method')

    return render_template('cart.html',
                           cart=cart,
                           address=address,
                           tab=tab,
                           receipt=receipt,
                           payment_method=payment_method)


# Lưu địa chỉ giao hàng
@app.route('/submit-address', methods=['POST'])
@login_required
def submit_address():
    house_number = request.form.get('house_number')
    street = request.form.get('street')
    ward = request.form.get('ward')
    district = request.form.get('district')
    city = request.form.get('city')
    country = request.form.get('country')

    if current_user.address:
        current_user.address.house_number = house_number
        current_user.address.street = street
        current_user.address.ward = ward
        current_user.address.district = district
        current_user.address.city = city
        current_user.address.country = country
    else:
        new_address = Address(
            house_number=house_number,
            street=street,
            ward=ward,
            district=district,
            city=city,
            country=country,
            user_id=current_user.id
        )
        db.session.add(new_address)

    db.session.commit()
    flash('Địa chỉ đã được lưu thành công!', 'success')
    return redirect(url_for('finalize_order'))


# Tạo hóa đơn
@app.route('/finalize_order', methods=['GET', 'POST'])
@login_required
def finalize_order():
    cart_key = f'cart_{current_user.id}'
    cart = session.get(cart_key, [])
    if not cart:
        flash('Giỏ hàng trống!', 'warning')
        return redirect(url_for('checkout', tab='cart'))

    payment_method = session.get('payment_method', 'offline')
    total = sum(item['price'] * item['quantity'] for item in cart)

    receipt = Receipt(user_id=current_user.id, total_price=total)
    db.session.add(receipt)
    db.session.flush()

    for item in cart:
        db.session.add(ReceiptDetail(
            receipt_id=receipt.id,
            book_id=item['id'],
            quantity=item['quantity'],
            unit_price=item['price']
        ))

    db.session.commit()
    session.pop(cart_key, None)
    session.pop('payment_method', None)

    return redirect(url_for('checkout', tab='result', receipt_id=receipt.id, method=payment_method))

if __name__ == "__main__":
    app.run(debug=True)