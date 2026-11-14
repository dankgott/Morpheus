import math
import os
import secrets

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from extensions import db
from models import User, Transaction, Product, Customer, Notification
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db.init_app(app)

with app.app_context():
    db.create_all()
    notification_columns = {
        column['name'] for column in inspect(db.engine).get_columns(Notification.__tablename__)
    }
    if 'is_read' not in notification_columns:
        try:
            db.session.execute(text(
                'ALTER TABLE notification ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0'
            ))
            db.session.commit()
        except OperationalError:
            db.session.rollback()
            migrated_columns = {
                column['name'] for column in inspect(db.engine).get_columns(Notification.__tablename__)
            }
            if 'is_read' not in migrated_columns:
                raise

LOW_STOCK_THRESHOLD = 10

@app.route('/')
def home():
    products = Product.query.order_by(Product.stock.asc(), Product.name.asc()).all()
    customers = Customer.query.options(
        selectinload(Customer.transactions)
    ).order_by(Customer.name.asc()).limit(5).all()
    transactions = Transaction.query.options(
        selectinload(Transaction.customer),
        selectinload(Transaction.product),
    ).order_by(Transaction.id.desc()).limit(7).all()
    transactions.reverse()
    total_sales = db.session.query(func.coalesce(func.sum(Transaction.total_amount), 0)).scalar()
    return render_template(
        'dashboard.html',
        products=products[:4],
        customers=customers,
        transactions=transactions,
        transaction_count=Transaction.query.count(),
        total_sales=total_sales,
        max_sales=max((transaction.total_amount for transaction in transactions), default=0) or 1,
    )

@app.route('/overview')
def overview():
    total_sales = db.session.query(func.coalesce(func.sum(Transaction.total_amount), 0)).scalar()
    transactions = Transaction.query.options(
        selectinload(Transaction.customer),
        selectinload(Transaction.product),
    ).order_by(Transaction.id.desc()).all()
    total_transactions = len(transactions)
    products = Product.query.order_by(Product.stock.asc(), Product.name.asc()).all()
    low_stock_count = sum(product.stock <= LOW_STOCK_THRESHOLD for product in products)
    trend_transactions = transactions[:7]
    trend_transactions.reverse()
    top_products = db.session.query(
        Product,
        func.coalesce(func.sum(Transaction.quantity), 0).label('units_sold'),
        func.coalesce(func.sum(Transaction.total_amount), 0).label('sales_total'),
    ).outerjoin(Transaction).group_by(Product.id).order_by(
        func.coalesce(func.sum(Transaction.total_amount), 0).desc()
    ).limit(5).all()
    return render_template(
        'overview.html',
        page_key='overview',
        page_title='Overview',
        total_sales=total_sales,
        total_transactions=total_transactions,
        customers_count=Customer.query.count(),
        low_stock_count=low_stock_count,
        top_products=top_products,
        trend_transactions=trend_transactions,
        max_sales=max((transaction.total_amount for transaction in trend_transactions), default=0) or 1,
        recent_transactions=transactions[:5],
    )

@app.route('/sales')
def sales():
    transactions = Transaction.query.options(
        selectinload(Transaction.customer),
        selectinload(Transaction.product),
    ).order_by(Transaction.id.desc()).all()
    total_sales = sum(transaction.total_amount for transaction in transactions)
    average_sale = total_sales / len(transactions) if transactions else 0
    return render_template(
        'sales.html',
        page_key='sales',
        page_title='Sales reports',
        transactions=transactions,
        total_sales=total_sales,
        average_sale=average_sale,
    )

@app.route('/stock')
def stock():
    products = Product.query.order_by(Product.stock.asc(), Product.name.asc()).all()
    return render_template(
        'stock.html',
        page_key='stock',
        page_title='Stock',
        products=products,
        low_stock_threshold=LOW_STOCK_THRESHOLD,
    )

@app.route('/stock/<int:product_id>/restock', methods=['POST'])
def restock_product(product_id):
    product = db.get_or_404(Product, product_id)
    product.stock += 5
    db.session.add(Notification(message=f'{product.name} was restocked. Current stock: {product.stock}.'))
    db.session.commit()
    flash(f'{product.name} restocked. New quantity: {product.stock}.', 'success')
    return redirect(url_for('stock'))

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip() or None
        if not name or not email:
            flash('Name and email are required.', 'error')
        else:
            customer = Customer(name=name, email=email, phone=phone)
            db.session.add(customer)
            db.session.add(Notification(message=f'New customer added: {name}.'))
            db.session.commit()
            flash('Customer added.', 'success')
            return redirect(url_for('customers'))
    customers = Customer.query.options(
        selectinload(Customer.transactions).selectinload(Transaction.product)
    ).order_by(Customer.name.asc()).all()
    total_customer_sales = sum(
        transaction.total_amount
        for customer in customers
        for transaction in customer.transactions
    )
    return render_template(
        'customers.html',
        page_key='customers',
        page_title='Customers',
        customers=customers,
        total_customer_sales=total_customer_sales,
    )

@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        try:
            price = float(request.form.get('price', ''))
            stock = int(request.form.get('stock', ''))
        except ValueError:
            flash('Enter a valid product price and stock quantity.', 'error')
        else:
            name = request.form.get('name', '').strip()
            sku = request.form.get('sku', '').strip()
            category = request.form.get('category', '').strip()
            if not name or not sku or not category or not math.isfinite(price) or price < 0 or stock < 0:
                flash('Enter a name, SKU, category, non-negative price, and non-negative stock.', 'error')
            else:
                product = Product(name=name, sku=sku, category=category, price=price, stock=stock)
                db.session.add(product)
                if stock == 0:
                    db.session.add(Notification(message=f'{name} was added out of stock.'))
                elif stock <= LOW_STOCK_THRESHOLD:
                    db.session.add(Notification(message=f'{name} was added with low stock ({stock} units).'))
                db.session.commit()
                flash('Product added.', 'success')
                return redirect(url_for('products'))
    products = Product.query.order_by(Product.name.asc()).all()
    average_price = sum(product.price for product in products) / len(products) if products else 0
    category_count = db.session.query(func.count(func.distinct(Product.category))).scalar()
    return render_template(
        'products.html',
        page_key='products',
        page_title='Products',
        products=products,
        category_count=category_count,
        average_price=average_price,
        low_stock_threshold=LOW_STOCK_THRESHOLD,
    )

@app.route('/transactions', methods=['GET', 'POST'])
def transactions():
    if request.method == 'POST':
        try:
            customer_id = int(request.form.get('customer_id', ''))
            product_id = int(request.form.get('product_id', ''))
            quantity = int(request.form.get('quantity', ''))
        except ValueError:
            flash('Choose a customer and product, and enter a valid quantity.', 'error')
        else:
            customer = db.session.get(Customer, customer_id)
            product = db.session.get(Product, product_id)
            if customer is None or product is None or quantity < 1:
                flash('Choose a valid customer and product and enter a quantity greater than zero.', 'error')
            elif product.stock < quantity:
                flash(f'Only {product.stock} units of {product.name} are in stock.', 'error')
            else:
                previous_stock = product.stock
                product.stock -= quantity
                db.session.add(Transaction(
                    customer_id=customer.id,
                    product_id=product.id,
                    quantity=quantity,
                    total_amount=product.price * quantity,
                ))
                db.session.add(Notification(
                    message=f'Sale recorded: {quantity} × {product.name} for ${product.price * quantity:.2f}.'
                ))
                if product.stock == 0:
                    db.session.add(Notification(message=f'{product.name} is out of stock.'))
                elif previous_stock > LOW_STOCK_THRESHOLD and product.stock <= LOW_STOCK_THRESHOLD:
                    db.session.add(Notification(
                        message=f'{product.name} is low on stock ({product.stock} units remaining).'
                    ))
                db.session.commit()
                flash('Sale recorded.', 'success')
                return redirect(url_for('transactions'))
    transactions = Transaction.query.options(
        selectinload(Transaction.customer),
        selectinload(Transaction.product),
    ).order_by(Transaction.id.desc()).all()
    customers = Customer.query.order_by(Customer.name.asc()).all()
    products = Product.query.filter(Product.stock > 0).order_by(Product.name.asc()).all()
    total_sales = sum(transaction.total_amount for transaction in transactions)
    average_sale = total_sales / len(transactions) if transactions else 0
    return render_template(
        'transactions.html',
        page_key='transactions',
        page_title='Transactions',
        transactions=transactions,
        customers=customers,
        products=products,
        total_sales=total_sales,
        average_sale=average_sale,
    )

@app.route('/api/data', methods=['GET'])
def get_data():
    # Sample data to return
    data = {
        'message': 'Hello, World!',
        'status': 'success'
    }
    return jsonify(data)

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    user_list = [{'id': user.id, 'username': user.username, 'email': user.email} for user in users]
    return jsonify(user_list)

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    transactions = Transaction.query.all()
    transaction_list = [{'id': t.id, 'customer_id': t.customer_id, 'product_id': t.product_id, 'quantity': t.quantity, 'total_amount': t.total_amount} for t in transactions]
    return jsonify(transaction_list)

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    product_list = [{'id': p.id, 'name': p.name, 'sku': p.sku, 'category': p.category, 'price': p.price, 'stock': p.stock} for p in products]
    return jsonify(product_list)

@app.route('/api/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    customer_list = [{'id': c.id, 'name': c.name, 'email': c.email, 'phone': c.phone} for c in customers]
    return jsonify(customer_list)

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    notifications = Notification.query.order_by(Notification.timestamp.desc(), Notification.id.desc()).limit(30).all()
    unread_count = Notification.query.filter_by(is_read=False).count()
    return jsonify({
        'unread_count': unread_count,
        'notifications': [{
            'id': notification.id,
            'message': notification.message,
            'timestamp': notification.timestamp.isoformat(),
            'is_read': notification.is_read,
        } for notification in notifications],
    })

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    notification = db.get_or_404(Notification, notification_id)
    notification.is_read = True
    db.session.commit()
    return jsonify({'id': notification.id, 'is_read': notification.is_read})

@app.route('/api/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    Notification.query.filter_by(is_read=False).update(
        {Notification.is_read: True},
        synchronize_session=False,
    )
    db.session.commit()
    return jsonify({'unread_count': 0})

@app.route('/api/transactions/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if transaction:
        transaction_data = {
            'id': transaction.id,
            'customer_id': transaction.customer_id,
            'product_id': transaction.product_id,
            'quantity': transaction.quantity,
            'total_amount': transaction.total_amount
        }
        return jsonify(transaction_data)
    else:
        return jsonify({'error': 'Transaction not found'}), 404
    
# 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# 500 error handler
@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)