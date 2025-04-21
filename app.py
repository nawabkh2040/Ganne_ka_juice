from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import os
import hashlib
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ganne_juice.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PayU configuration
PAYU_MERCHANT_KEY = os.getenv('PAYU_MERCHANT_KEY')
PAYU_MERCHANT_SALT = os.getenv('PAYU_MERCHANT_SALT')
PAYU_ENV = os.getenv('PAYU_ENV', 'test')  # 'test' or 'production'
PAYU_BASE_URL = 'https://test.payu.in' if PAYU_ENV == 'test' else 'https://info.payu.in'
PRICE_PER_CUP = 2500  # ₹25.00 in paise

def generate_payu_hash(txnid, amount, productinfo, firstname, email, salt):
    """Generate PayU hash for payment verification"""
    # Create the hash string with all required fields in exact order
    # Format: sha512(key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||SALT)
    hash_string = f"{PAYU_MERCHANT_KEY}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|||||||||||{salt}"
    print(f"Hash string: {hash_string}")  # Debug print
    
    # Generate SHA-512 hash
    hash_value = hashlib.sha512(hash_string.encode()).hexdigest().lower()
    print(f"Generated hash: {hash_value}")  # Debug print
    
    # Generate v1 and v2 hashes as required by PayU
    v1_hash = hash_value
    v2_hash = hashlib.sha512(f"{v1_hash}|{salt}".encode()).hexdigest().lower()
    
    print(f"v1 hash: {v1_hash}")  # Debug print
    print(f"v2 hash: {v2_hash}")  # Debug print
    
    return {
        "v1": v1_hash,
        "v2": v2_hash
    }

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'seller'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    verification_code = db.Column(db.String(6), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, ready, completed
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, failed
    stripe_payment_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Integer, nullable=False)  # Amount in paise

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        user = User.query.filter_by(username=username, role=role).first()
        
        if user and user.check_password(password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('seller_dashboard'))
        flash('Invalid username, password, or role')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html')

@app.route('/seller/dashboard')
@login_required
def seller_dashboard():
    if current_user.role != 'seller':
        return redirect(url_for('home'))
    orders = Order.query.filter_by(status='pending', payment_status='paid').all()
    return render_template('seller.html', orders=orders)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/create-payment', methods=['POST'])
def create_payment():
    try:
        data = request.json
        quantity = int(data['quantity'])
        total_amount = quantity * PRICE_PER_CUP

        # Store order details in session for later use
        session['order_details'] = {
            'name': data['name'],
            'phone': data['phone'],
            'quantity': quantity,
            'total_amount': total_amount
        }

        # Create PayU payment request
        txnid = ''.join(random.choices(string.digits, k=10))
        productinfo = f'{quantity} cup(s) of fresh sugarcane juice'
        email = f"{data['phone']}@gannejuice.com"
        amount = str(total_amount/100)  # Convert to rupees

        # Generate hash
        hash_values = generate_payu_hash(
            txnid=txnid,
            amount=amount,
            productinfo=productinfo,
            firstname=data['name'],
            email=email,
            salt=PAYU_MERCHANT_SALT
        )

        payment_data = {
            'key': PAYU_MERCHANT_KEY,
            'txnid': txnid,
            'amount': amount,
            'productinfo': productinfo,
            'firstname': data['name'],
            'email': email,
            'phone': data['phone'],
            'surl': url_for('success', _external=True),
            'furl': url_for('cancel', _external=True),
            'hash': hash_values['v1'],  # Use v1 hash for payment
            'service_provider': 'payu_paisa'
        }

        # Debug print
        print(f"Payment data: {payment_data}")

        return jsonify(payment_data)
    except Exception as e:
        print(f"Error: {str(e)}")  # Debug print
        return jsonify(error=str(e)), 403

@app.route('/check-transaction/<txnid>')
@login_required
def check_transaction(txnid):
    try:
        # Generate hash for transaction check
        hash_string = f"{PAYU_MERCHANT_KEY}|verify_payment|{txnid}|{PAYU_MERCHANT_SALT}"
        hash_value = hashlib.sha512(hash_string.encode()).hexdigest().lower()

        # Make API request to check transaction status
        response = requests.post(
            f"{PAYU_BASE_URL}/merchant/postservice.php?form=2",
            data={
                'key': PAYU_MERCHANT_KEY,
                'command': 'verify_payment',
                'var1': txnid,
                'hash': hash_value
            }
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.route('/refund/<txnid>', methods=['POST'])
@login_required
def refund_transaction(txnid):
    try:
        data = request.json
        refund_amount = data.get('amount')
        
        # Generate hash for refund
        hash_string = f"{PAYU_MERCHANT_KEY}|{txnid}|{refund_amount}|{PAYU_MERCHANT_SALT}"
        hash_value = hashlib.sha512(hash_string.encode()).hexdigest().lower()

        # Make API request for refund
        response = requests.post(
            f"{PAYU_BASE_URL}/merchant/postservice.php?form=2",
            data={
                'key': PAYU_MERCHANT_KEY,
                'command': 'refund_payment',
                'var1': txnid,
                'var2': refund_amount,
                'hash': hash_value
            }
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.route('/success')
def success():
    # Get order details from session
    order_details = session.get('order_details')
    if not order_details:
        return redirect(url_for('home'))

    verification_code = generate_verification_code()
    
    # Create new order
    new_order = Order(
        customer_name=order_details['name'],
        phone_number=order_details['phone'],
        quantity=order_details['quantity'],
        verification_code=verification_code,
        total_amount=order_details['total_amount'],
        payment_status='paid'
    )
    
    db.session.add(new_order)
    db.session.commit()

    # Clear session
    session.pop('order_details', None)

    return render_template('success.html', 
                         verification_code=verification_code,
                         order_id=new_order.id)

@app.route('/cancel')
def cancel():
    return redirect(url_for('home'))

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    data = request.json
    order = Order.query.get(data['order_id'])
    if order:
        order.status = data['status']
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/verify_order', methods=['POST'])
def verify_order():
    data = request.json
    order = Order.query.filter_by(
        id=data['order_id'],
        verification_code=data['code']
    ).first()
    
    if order:
        order.status = 'completed'
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')  # Change this password in production
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
