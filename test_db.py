#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['USE_SQLITE'] = 'true'

from database import get_db, User

def test_users():
    try:
        db = next(get_db())
        users = db.query(User).all()
        print("Current users in database:")
        for user in users:
            print(f'User ID: {user.user_id}, Username: {user.username}, Has Password: {user.password is not None}')
        db.close()
    except Exception as e:
        print(f'Error: {str(e)}')

if __name__ == '__main__':
    test_users()
