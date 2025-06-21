#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['USE_SQLITE'] = 'true'

from database import get_db, User, hash_password, verify_password

def debug_password_issue():
    """Debug the password verification issue for testuser"""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.user_id == 'testuser').first()
        
        if user:
            print(f'User found: {user.user_id}')
            print(f'Username: {user.username}')
            print(f'Has password: {user.password is not None}')
            print(f'Stored password hash: {user.password}')
            print(f'Hash starts with: {user.password[:20]}...' if user.password else 'No password')
            print()
            
            test_hash = hash_password('testpass123')
            print(f'New hash for "testpass123": {test_hash}')
            print(f'New hash starts with: {test_hash[:20]}...')
            print()
            
            verification_result = verify_password('testpass123', user.password)
            print(f'Verify "testpass123" against stored hash: {verification_result}')
            
            new_verification = verify_password('testpass123', test_hash)
            print(f'Verify "testpass123" against new hash: {new_verification}')
            
            wrong_verification = verify_password('wrongpass', user.password)
            print(f'Verify "wrongpass" against stored hash: {wrong_verification}')
            
        else:
            print('testuser not found in database')
        
        db.close()
        
    except Exception as e:
        print(f'Error during password debugging: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_password_issue()
