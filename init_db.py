from app import app, db, User, Order
import os
from werkzeug.security import generate_password_hash

def init_db():
    # Create database directory if it doesn't exist
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Create all tables
    with app.app_context():
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            print("Admin user created successfully!")

        # Create seller user if it doesn't exist
        seller = User.query.filter_by(username='seller').first()
        if not seller:
            seller = User(
                username='seller',
                password_hash=generate_password_hash('seller123'),
                role='seller'
            )
            db.session.add(seller)
            print("Seller user created successfully!")

        db.session.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!") 