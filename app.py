from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random
import string
import stripe
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ganne_juice.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
PRICE_PER_CUP = 2500  # ₹25.00 in paise

YOUR_DOMAIN = os.getenv('YOUR_DOMAIN', 'http://localhost:5000')

db = SQLAlchemy(app)

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

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

@app.route('/')
def home():
    return render_template('index.html', stripe_public_key=STRIPE_PUBLISHABLE_KEY)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
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

        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': 'Ganne ka Juice',
                        'description': f'{quantity} cup(s) of fresh sugarcane juice'
                    },
                    'unit_amount': PRICE_PER_CUP,
                },
                'quantity': quantity,
            }],
            mode='payment',
            payment_method_types=['card'],
            success_url=YOUR_DOMAIN + '/success',
            cancel_url=YOUR_DOMAIN + '/cancel',
        )
        return jsonify({'sessionId': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

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

@app.route('/seller')
def seller_view():
    orders = Order.query.filter_by(status='pending', payment_status='paid').all()
    return render_template('seller.html', orders=orders)

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
    app.run(debug=True)
