#!/usr/bin/env python3
"""
Script to create test users with hashed passwords for testing login functionality
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['USE_SQLITE'] = 'true'

from database import get_db, User, hash_password, create_tables

def create_test_users():
    """Create test users with hashed passwords"""
    try:
        create_tables()
        
        db = next(get_db())
        
        existing_user = db.query(User).filter(User.user_id == 'testuser').first()
        if existing_user:
            print('Test user already exists, updating password...')
            existing_user.password = hash_password('testpass123')
        else:
            print('Creating new test user...')
            test_user = User(
                user_id='testuser',
                username='Test User',
                password=hash_password('testpass123'),
                token_limit=10000,
                has_appointment=False
            )
            db.add(test_user)
        
        existing_admin = db.query(User).filter(User.user_id == 'admin').first()
        if existing_admin:
            print('Admin user already exists, updating password...')
            existing_admin.password = hash_password('admin123')
            existing_admin.is_admin = True
        else:
            print('Creating admin test user...')
            admin_user = User(
                user_id='admin',
                username='Administrator',
                password=hash_password('admin123'),
                is_admin=True,
                token_limit=0,
                has_appointment=False
            )
            db.add(admin_user)
        
        db.commit()
        db.close()
        
        print('Test users created successfully!')
        print('Test user: testuser / testpass123')
        print('Admin user: admin / admin123')
        
    except Exception as e:
        print(f'Error creating test users: {str(e)}')

if __name__ == '__main__':
    create_test_users()
