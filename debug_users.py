#!/usr/bin/env python3
"""
Script to debug user database contents
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['USE_SQLITE'] = 'true'

from database import get_db, User

def debug_users():
    """Debug user database contents"""
    try:
        db = next(get_db())
        users = db.query(User).all()
        print(f"Total users found: {len(users)}")
        
        for user in users:
            print(f"User: {user.user_id}, Username: {user.username}, Has Password: {user.password is not None}")
            if user.password:
                print(f"Password hash: {user.password[:50]}...")
        
        db.close()
        
    except Exception as e:
        print(f'Error debugging users: {str(e)}')

if __name__ == '__main__':
    debug_users()
