import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from database import User, Template, Base, engine
from urllib.parse import quote_plus
from config import USE_SQLITE

def initialize_database():
    """初始化数据库 - 创建表结构并添加初始数据"""
    from dotenv import load_dotenv
    load_dotenv()
    
    if USE_SQLITE:
        DATABASE_URL = "sqlite:///chatbot.db"
        print(f"使用SQLite数据库: {DATABASE_URL}")
    else:
        DB_USER = os.getenv("DB_USER", "pkwgc")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "Wghfd@584521@fd")
        DB_HOST = os.getenv("DB_HOST", "rm-m5e0666vtv5234qi39o.mysql.rds.aliyuncs.com")
        DB_PORT = os.getenv("DB_PORT", "3306")
        DB_NAME = os.getenv("DB_NAME", "chatbot")
        
        encoded_password = quote_plus(DB_PASSWORD)
        DATABASE_URL = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    try:
        if USE_SQLITE:
            print(f"连接到SQLite数据库...")
            engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        else:
            print(f"连接到数据库: {DB_HOST}...")
            engine = create_engine(DATABASE_URL)
        
        print("创建数据库表...")
        Base.metadata.create_all(bind=engine)
        print("数据库表创建成功！")
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        db.execute(text("SELECT 1"))
        print("数据库连接成功！")
        
        try:
            admin = db.query(User).filter(User.user_id == 'admin').first()
            if not admin:
                print("创建管理员用户...")
                admin = User(user_id='admin', username='管理员', is_admin=True)
                db.add(admin)
                db.commit()
                print("管理员用户创建成功！")
            else:
                print("管理员用户已存在，跳过创建。")
            
            print("数据库初始化完成！请通过后台管理界面创建所需的模板。")
        
        except Exception as e:
            print(f"初始化数据时出错：{str(e)}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"连接数据库时出错：{str(e)}")

def update_user_table():
    """更新用户表结构，添加身份和爱好字段"""
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        with engine.connect() as conn:
            if USE_SQLITE:
                if 'identity' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN identity VARCHAR(200)"))
                    print("已添加identity字段")
                    
                if 'hobbies' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN hobbies VARCHAR(500)"))
                    print("已添加hobbies字段")
                    
                if 'profile_data' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN profile_data TEXT"))
                    print("已添加profile_data字段")
                    
                if 'password' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password VARCHAR(255)"))
                    print("已添加password字段")
            else:
                if 'identity' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN identity VARCHAR(200) NULL"))
                    print("已添加identity字段")
                    
                if 'hobbies' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN hobbies VARCHAR(500) NULL"))
                    print("已添加hobbies字段")
                    
                if 'profile_data' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN profile_data TEXT NULL"))
                    print("已添加profile_data字段")
                    
                if 'password' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password VARCHAR(255) NULL"))
                    print("已添加password字段")
            
            try:
                conn.commit()
            except:
                pass
            print("用户表结构更新完成")
    except Exception as e:
        print(f"更新用户表结构失败: {str(e)}")

def update_inventory_tables():
    """更新库存相关表结构"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        with engine.connect() as conn:
            if USE_SQLITE:
                if 'inventory_items' not in tables:
                    print("创建inventory_items表...")
                    conn.execute(text("""
                    CREATE TABLE inventory_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        inventory_upload_id INTEGER,
                        product_name VARCHAR(255) NOT NULL,
                        product_id VARCHAR(100),
                        quantity INTEGER DEFAULT 0,
                        price FLOAT,
                        total_price FLOAT,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (inventory_upload_id) REFERENCES inventory_uploads(id) ON DELETE CASCADE
                    )
                    """))
                    print("inventory_items表创建成功")
                else:
                    print("inventory_items表已存在")
                    
                if 'orders' not in tables:
                    print("创建orders表...")
                    conn.execute(text("""
                    CREATE TABLE orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        order_number VARCHAR(50) UNIQUE,
                        total_amount FLOAT DEFAULT 0.0,
                        status VARCHAR(20) DEFAULT 'pending',
                        payment_status VARCHAR(20) DEFAULT 'unpaid',
                        payment_method VARCHAR(50),
                        shipping_address TEXT,
                        contact_info VARCHAR(100),
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """))
                    print("orders表创建成功")
                else:
                    print("orders表已存在")
                    
                if 'order_items' not in tables:
                    print("创建order_items表...")
                    conn.execute(text("""
                    CREATE TABLE order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER,
                        product_name VARCHAR(255) NOT NULL,
                        product_id VARCHAR(100),
                        quantity INTEGER DEFAULT 1,
                        price FLOAT DEFAULT 0.0,
                        total_price FLOAT DEFAULT 0.0,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                    )
                    """))
                    print("order_items表创建成功")
                else:
                    print("order_items表已存在")
                    
                if 'sales' not in tables:
                    print("创建sales表...")
                    conn.execute(text("""
                    CREATE TABLE sales (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        order_id INTEGER,
                        product_name VARCHAR(255) NOT NULL,
                        product_id VARCHAR(100),
                        quantity INTEGER DEFAULT 1,
                        price FLOAT DEFAULT 0.0,
                        total_amount FLOAT DEFAULT 0.0,
                        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        payment_method VARCHAR(50),
                        notes TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
                    )
                    """))
                    print("sales表创建成功")
                else:
                    print("sales表已存在")
            else:
                if 'inventory_items' not in tables:
                    print("创建inventory_items表...")
                    conn.execute(text("""
                    CREATE TABLE inventory_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        inventory_upload_id INT,
                        product_name VARCHAR(255) NOT NULL,
                        product_id VARCHAR(100),
                        quantity INT DEFAULT 0,
                        price FLOAT,
                        total_price FLOAT,
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (inventory_upload_id) REFERENCES inventory_uploads(id) ON DELETE CASCADE
                    )
                    """))
                    print("inventory_items表创建成功")
                else:
                    print("inventory_items表已存在")
                    
                if 'orders' not in tables:
                    print("创建orders表...")
                    conn.execute(text("""
                    CREATE TABLE orders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        order_number VARCHAR(50) UNIQUE,
                        total_amount FLOAT DEFAULT 0.0,
                        status VARCHAR(20) DEFAULT 'pending',
                        payment_status VARCHAR(20) DEFAULT 'unpaid',
                        payment_method VARCHAR(50),
                        shipping_address TEXT,
                        contact_info VARCHAR(100),
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """))
                    print("orders表创建成功")
                else:
                    print("orders表已存在")
                    
                if 'order_items' not in tables:
                    print("创建order_items表...")
                    conn.execute(text("""
                    CREATE TABLE order_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT,
                        product_name VARCHAR(255) NOT NULL,
                        product_id VARCHAR(100),
                        quantity INT DEFAULT 1,
                        price FLOAT DEFAULT 0.0,
                        total_price FLOAT DEFAULT 0.0,
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                    )
                    """))
                    print("order_items表创建成功")
                else:
                    print("order_items表已存在")
                    
                if 'sales' not in tables:
                    print("创建sales表...")
                    conn.execute(text("""
                    CREATE TABLE sales (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        order_id INT,
                        product_name VARCHAR(255) NOT NULL,
                        product_id VARCHAR(100),
                        quantity INT DEFAULT 1,
                        price FLOAT DEFAULT 0.0,
                        total_amount FLOAT DEFAULT 0.0,
                        sale_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        payment_method VARCHAR(50),
                        notes TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
                    )
                    """))
                    print("sales表创建成功")
                else:
                    print("sales表已存在")
            
            try:
                conn.commit()
            except:
                pass
            print("库存和订单相关表结构更新完成")
    except Exception as e:
        print(f"更新库存和订单相关表结构失败: {str(e)}")

if __name__ == "__main__":
    initialize_database()
    update_user_table()
    update_inventory_tables()
