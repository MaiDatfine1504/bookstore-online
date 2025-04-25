from flask import render_template, abort, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import extract, func
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from app import app, db, login
from models import Book, Genre, User, UserEnum, Rule, Receipt, ReceiptDetail, Address, OrderStatusEnum, PaymentMethodEnum
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
            elif user.role == UserEnum.EMPLOYEE:
                return redirect(url_for('employee_dashboard'))
            else:
                return redirect(url_for('homepage'))
        else:
            flash("Sai thông tin đăng nhập!", "danger")
    return render_template("account/login.html")

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

    return render_template("account/register.html")

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

# Hàm cập nhật đơn hàng quá hạn
def update_expired_offline_orders():
    now = datetime.now()
    expired_time = now - Rule.cancel_time

    expired_orders = Receipt.query.filter(
        Receipt.created_date < expired_time,
        Receipt.status == OrderStatusEnum.PENDING,
        Receipt.payment_method == PaymentMethodEnum.OFFLINE
    ).all()

    for order in expired_orders:
        order.status = OrderStatusEnum.CANCELED

    if expired_orders:
        db.session.commit()

# Quản lý đặt hàng
@app.route('/api/orders', methods=['GET'])
def get_orders():
    update_expired_offline_orders()  # Gọi trước khi trả dữ liệu

    receipts = Receipt.query.all()

    result = []
    for r in receipts:
        result.append({
            'id': r.id,
            'buyer_name': r.user.name if r.user else "Không xác định",
            'date': r.created_date.strftime("%Y-%m-%d %H:%M"),
            'total': r.total_price,
            'status': r.status.value
        })

    return jsonify(result)

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order_detail(order_id):
    # Cập nhật trạng thái quá hạn như trước
    update_expired_offline_orders()
    
    # Lấy receipt
    receipt = Receipt.query.get(order_id)
    if not receipt:
        return abort(404, description="Order not found")
    
    # Lấy chi tiết
    details = ReceiptDetail.query.filter_by(receipt_id=order_id).all()
    result = []
    for d in details:
        # giả sử Book relationship đã được thiết lập
        book = Book.query.get(d.book_id)
        result.append({
            'book_title': book.title if book else 'Không xác định',
            'quantity': d.quantity,
            'unit_price': d.unit_price,
            'subtotal': d.quantity * d.unit_price
        })
    return jsonify(result)


#Điều hướng tới form employee
@app.route('/employee/dashboard')
def employee_dashboard():
    return render_template('dashboard/employee.html')

#Đếm sách khi quét mã vạch
@app.route('/counter', methods=['GET', 'POST'])
@login_required
def counter():
    if current_user.role != UserEnum.EMPLOYEE:
        flash("Chỉ nhân viên quầy mới được truy cập trang này.", "warning")
        return redirect(url_for('homepage'))

    cart_key = f'counter_cart_{current_user.id}'
    cart = session.get(cart_key, [])

    if request.method == 'POST':
        raw = request.form.get('barcode', '').strip()
        try:
            book_id = int(raw)
            book = Book.query.get(book_id)
        except (ValueError, TypeError):
            book = None

        if not book:
            flash(f"Không tìm thấy sách với ID: {raw}", "danger")
        else:
            # Thêm sách vào giỏ tạm
            existing = next((i for i in cart if i['id'] == book.id), None)
            if existing:
                existing['quantity'] += 1
            else:
                cart.append({
                    'id': book.id,
                    'title': book.title,
                    'author': book.author,
                    'price': book.price,
                    'quantity': 1
                })
            session[cart_key] = cart
            session.modified = True
            flash(f"Đã thêm «{book.title}» vào giỏ.", "success")

    return render_template('dashboard/employee.html', cart=cart)

@app.route('/finalize_counter_order', methods=['POST'])
@login_required
def finalize_counter_order():
    if current_user.role != UserEnum.EMPLOYEE:
        return redirect(url_for('homepage'))

    cart_key = f'counter_cart_{current_user.id}'
    cart = session.get(cart_key, [])
    if not cart:
        flash("Giỏ hàng trống!", "warning")
        return redirect(url_for('counter'))

    total = sum(item['price'] * item['quantity'] for item in cart)
    receipt = Receipt(user_id=current_user.id, total_price=total, status=OrderStatusEnum.COMPLETED)
    db.session.add(receipt)
    db.session.flush()
    for item in cart:
        db.session.add(ReceiptDetail(
            receipt_id=receipt.id,
            book_id=item['id'],
            quantity=item['quantity'],
            unit_price=item['price'],
        ))
    db.session.commit()

    # Xoá giỏ tạm
    session.pop(cart_key, None)
    flash(f"In hoá đơn #{receipt.id} thành công!", "success")
    return redirect(url_for('counter'))

#Điều hướng tới trang chủ
@app.route("/")
def homepage():
    books = Book.query.order_by(func.random()).limit(6).all()
    return render_template('user/homepage.html', books=books)

#Điều hướng tới trang thông tin sách
@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get(book_id)
    if book is None:
        abort(404)
    return render_template('user/book_detail.html', book=book)

#Hiển thị toàn bộ sách cùng thể loại
@app.route('/genre/<int:genre_id>')
def books_by_genre(genre_id):
    books = Book.query.filter_by(genre_id=genre_id).all()
    genre = Genre.query.get(genre_id)
    
    if not genre:
        abort(404)

    return render_template('user/homepage.html', books=books, genre=genre)

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

    return render_template('user/homepage.html', books=books)

#Thêm sách vào giỏ hàng
@app.route('/add-to-cart/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    if current_user.role != UserEnum.USER:
        flash("Chỉ người dùng mới có thể thêm vào giỏ hàng.", "warning")
        return redirect(url_for('homepage'))

    # Lấy số lượng và sách
    quantity = request.form.get('quantity', 1, type=int)
    book = Book.query.get_or_404(book_id)

    # Thêm vào session cart
    cart_key = f'cart_{current_user.id}'
    cart = session.get(cart_key, [])
    existing = next((i for i in cart if i['id'] == book.id), None)
    if existing:
        existing['quantity'] += quantity
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

#Xoá sách khỏi giỏ hàng
@app.route('/remove-from-cart/<int:book_id>', methods=['POST'])
@login_required
def remove_from_cart(book_id):
    cart_key = f'cart_{current_user.id}'
    cart = session.get(cart_key, [])

    # Lọc bỏ hết các mục có id == book_id
    new_cart = [item for item in cart if item['id'] != book_id]

    if new_cart:
        # Nếu vẫn còn sách khác, lưu lại giỏ mới
        session[cart_key] = new_cart
    else:
        # Nếu giỏ trống, xoá hẳn key khỏi session
        session.pop(cart_key, None)

    # Đánh dấu session đã thay đổi
    session.modified = True

    flash('Đã xóa sách khỏi giỏ hàng.', 'success')
    return redirect(url_for('checkout', tab='cart'))

#Xem giỏ hàng
@app.route('/cart')
@login_required
def view_cart():
    if current_user.role != UserEnum.USER:
        flash("Chỉ người dùng mới được xem giỏ hàng.", "warning")
        return redirect(url_for('homepage'))

    cart_key = f'cart_{current_user.id}'
    cart = session.get(cart_key, [])
    return redirect(url_for('checkout', tab='cart'))

#Hiển thị và xử lý thanh toán
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    tab = request.args.get('tab', 'cart')
    cart_key = f'cart_{current_user.id}'
    selected_key = f'selected_cart_{current_user.id}'
    cart = session.get(selected_key) or session.get(cart_key, [])

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        session['payment_method'] = payment_method

        # Chuyển đến tab địa chỉ nếu chọn thanh toán online
        if payment_method == 'online':
            return redirect(url_for('checkout', tab='address'))
        else:
            # Nếu thanh toán khi nhận hàng, chuyển đến trang xác nhận đơn hàng
            return redirect(url_for('finalize_order'))

    # Lấy thông tin hóa đơn nếu có
    receipt = None
    receipt_id = request.args.get('receipt_id')
    if tab == 'result' and receipt_id:
        receipt = Receipt.query.get(receipt_id)

    # Lấy thông tin địa chỉ của người dùng
    address = None
    if current_user.address and tab in ['address', 'result']:
        address = {
            'house_number': current_user.address.house_number,
            'street': current_user.address.street,
            'ward': current_user.address.ward,
            'district': current_user.address.district,
            'city': current_user.address.city,
            'country': current_user.address.country
        }

    payment_method = session.get('payment_method') or request.args.get('method')

    return render_template('user/cart.html',
                           cart=cart,
                           address=address,
                           tab=tab,
                           receipt=receipt,
                           payment_method=payment_method)

#Chọn sách để thanh toán
@app.route('/checkout-selected', methods=['POST'])
@login_required
def checkout_selected():
    cart_key = f'cart_{current_user.id}'
    full_cart = session.get(cart_key, [])

    selected_ids = request.form.getlist('selected_books')
    if not selected_ids:
        flash('Bạn chưa chọn sách nào để thanh toán.', 'warning')
        return redirect(url_for('checkout', tab='cart'))

    # Chỉ lấy sách đã chọn từ giỏ hàng
    selected_cart = [item for item in full_cart if str(item['id']) in selected_ids]
    if not selected_cart:
        flash('Không tìm thấy sách đã chọn trong giỏ hàng.', 'danger')
        return redirect(url_for('checkout', tab='cart'))

    session[f'selected_cart_{current_user.id}'] = selected_cart
    return redirect(url_for('checkout', tab='method'))

#Lưu địa chỉ giao hàng
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

#Tạo hóa đơn thanh toán
@app.route('/finalize_order', methods=['GET', 'POST'])
@login_required
def finalize_order():
    cart_key = f'cart_{current_user.id}'
    selected_key = f'selected_cart_{current_user.id}'
    cart = session.get(selected_key) or session.get(cart_key, [])

    if not cart:
        flash('Giỏ hàng trống!', 'warning')
        return redirect(url_for('checkout', tab='cart'))

    payment_method = session.get('payment_method', 'offline')
    total = sum(item['price'] * item['quantity'] for item in cart)

    # Xác định trạng thái đơn
    if payment_method == 'online':
        status = OrderStatusEnum.COMPLETED
    else:
        status = OrderStatusEnum.PENDING

    # Tạo hóa đơn
    receipt = Receipt(
        user_id=current_user.id,
        total_price=total,
        payment_method=PaymentMethodEnum(payment_method),
        status=status,
    )
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

    # Giữ lại các sách chưa thanh toán trong giỏ
    full_cart = session.get(cart_key, [])
    remaining_cart = [item for item in full_cart if item not in cart]
    session[cart_key] = remaining_cart

    session.pop(selected_key, None)
    session.pop('payment_method', None)

    return redirect(url_for('checkout', tab='result', receipt_id=receipt.id, method=payment_method))

if __name__ == "__main__":
    app.run(debug=True)