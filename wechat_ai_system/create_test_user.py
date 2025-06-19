#!/usr/bin/env python3
import os
import sys
from datetime import datetime

os.environ['USE_SQLITE'] = 'true'

print('=== 创建测试用户 ===')

try:
    from database import get_db, User
    from werkzeug.security import generate_password_hash
    
    db = next(get_db())
    
    existing_user = db.query(User).filter(User.username == 'testuser').first()
    if existing_user:
        print('测试用户已存在，更新密码...')
        existing_user.password = generate_password_hash('password123')
        db.commit()
        print('✅ 测试用户密码已更新')
    else:
        test_user = User(
            user_id='testuser',
            username='testuser',
            password=generate_password_hash('password123'),
            is_admin=False,
            token_limit=1000,
            token_balance=1000
        )
        
        db.add(test_user)
        db.commit()
        print('✅ 测试用户创建成功')
    
    user = db.query(User).filter(User.username == 'testuser').first()
    if user:
        print(f'用户ID: {user.user_id}')
        print(f'用户名: {user.username}')
        print(f'管理员: {"是" if user.is_admin else "否"}')
        print(f'令牌限制: {user.token_limit}')
        print(f'令牌余额: {user.token_balance}')
    
    db.close()
    print('=== 测试用户创建完成 ===')
    
except Exception as e:
    print(f'❌ 创建测试用户失败: {e}')
    sys.exit(1)
