#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['USE_SQLITE'] = 'true'

from database import get_db, User, verify_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('routes.user_routes')

def debug_flask_password_verification():
    """Debug password verification exactly as Flask app does it"""
    try:
        user_id = 'testuser'
        password = 'testpass123'
        
        db = next(get_db())
        user = db.query(User).filter(User.user_id == user_id).first()
        
        print(f"=== Flask Context Password Debug ===")
        print(f"Login attempt for user_id: {user_id}")
        print(f"User found: {user is not None}")
        
        if user:
            print(f"User has password: {user.password is not None}")
            if user.password:
                verification_result = verify_password(password, user.password)
                print(f"Password verification: {verification_result}")
                
                login_success = user and user.password and verify_password(password, user.password)
                print(f"Login would succeed: {login_success}")
                
                wrong_verification = verify_password('wrongpass', user.password)
                print(f"Wrong password verification: {wrong_verification}")
            else:
                print("No password set for user")
        else:
            print("User not found")
        
        db.close()
        
    except Exception as e:
        print(f'Error during Flask context debugging: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_flask_password_verification()
