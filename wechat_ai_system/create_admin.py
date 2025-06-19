import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import User, Base
import hashlib

os.environ['USE_SQLITE'] = 'true'

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def create_admin_user():
    """创建管理员用户并设置密码"""
    try:
        admin = db.query(User).filter(User.user_id == 'admin').first()
        
        if not admin:
            print("创建管理员用户...")
            admin = User(
                user_id='admin',
                username='管理员',
                is_admin=True,
                token_limit=0,  # 0表示无限制
                token_balance=1000000,  # 给予足够的token余额
                has_appointment=True
            )
            db.add(admin)
        
        password = "admin123"
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        admin.password = hashed_password
        
        db.commit()
        print(f"管理员用户已创建/更新，用户名: admin，密码: {password}")
        
    except Exception as e:
        db.rollback()
        print(f"创建管理员用户时出错: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
