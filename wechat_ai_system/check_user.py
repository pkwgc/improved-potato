from database import get_db, User

def check_test_user():
    db = next(get_db())
    try:
        user = db.query(User).filter(User.user_id == 'testuser').first()
        if user:
            print(f'用户ID: {user.user_id}')
            print(f'用户名: {user.username}')
            print(f'角色: {user.role}')
            print(f'密码哈希: {user.password[:20]}...')
        else:
            print('用户不存在')
    finally:
        db.close()

if __name__ == '__main__':
    check_test_user()
