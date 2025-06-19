#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db, User
import hashlib

def check_admin_user():
    """检查管理员用户状态"""
    print("检查管理员用户...")
    
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.user_id == 'admin').first()
        if admin:
            print(f'管理员用户找到:')
            print(f'  user_id: {admin.user_id}')
            print(f'  username: {admin.username}')
            print(f'  password: {admin.password}')
            print(f'  is_admin: {admin.is_admin}')
            
            password = "admin123"
            password_hash = hashlib.md5(password.encode()).hexdigest()
            print(f'  期望的admin123密码哈希: {password_hash}')
            
            if not admin.password:
                print("管理员用户没有设置密码，正在设置...")
                admin.password = password_hash
                db.commit()
                print("密码设置完成！")
            elif admin.password != password_hash:
                print("管理员密码哈希不匹配，正在更新...")
                admin.password = password_hash
                db.commit()
                print("密码更新完成！")
            else:
                print("管理员密码已正确设置")
                
        else:
            print('管理员用户未找到')
            
    except Exception as e:
        print(f"检查失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_user()
