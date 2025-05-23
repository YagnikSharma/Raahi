"""
Fix Admin Login - Create proper admin accounts with correct password hashing
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import datetime

def create_admin_accounts():
    """Create admin accounts with proper password hashing"""
    with app.app_context():
        # Clear existing users
        User.query.delete()
        
        # Create admin accounts with proper password hashing
        admin_accounts = [
            {
                'username': 'admin',
                'email': 'admin@raahi.com',
                'password': 'admin123',
                'is_admin': True
            },
            {
                'username': 'safety_officer',
                'email': 'safety@raahi.com', 
                'password': 'safety123',
                'is_admin': True
            },
            {
                'username': 'operator1',
                'email': 'operator1@raahi.com',
                'password': 'operator123',
                'is_admin': True
            },
            {
                'username': 'emergency_coord',
                'email': 'emergency@raahi.com',
                'password': 'emergency123',
                'is_admin': True
            }
        ]
        
        print("🔐 Creating admin accounts with proper password hashing...")
        
        for account in admin_accounts:
            user = User(
                username=account['username'],
                email=account['email'],
                is_admin=account['is_admin'],
                created_at=datetime.datetime.utcnow() - datetime.timedelta(days=30),
                last_login=datetime.datetime.utcnow() - datetime.timedelta(hours=2)
            )
            # Use the model's set_password method for proper hashing
            user.set_password(account['password'])
            db.session.add(user)
            print(f"✅ Created: {account['username']} / {account['password']}")
        
        db.session.commit()
        print("\n🎉 Admin login accounts ready!")
        print("Login credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\n  Other accounts: safety_officer/safety123, operator1/operator123, emergency_coord/emergency123")

if __name__ == "__main__":
    create_admin_accounts()