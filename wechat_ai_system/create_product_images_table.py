import os
import sys
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URI

def create_product_images_table():
    """创建product_images表"""
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    
    sqlite_sql = """
    CREATE TABLE IF NOT EXISTS product_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inventory_item_id INTEGER,
        image_path VARCHAR(500),
        original_filename VARCHAR(255),
        file_size INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (inventory_item_id) REFERENCES inventory_items (id)
    );
    """
    
    mysql_sql = """
    CREATE TABLE IF NOT EXISTS product_images (
        id INT AUTO_INCREMENT PRIMARY KEY,
        inventory_item_id INT,
        image_path VARCHAR(500),
        original_filename VARCHAR(255),
        file_size INT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (inventory_item_id) REFERENCES inventory_items (id)
    );
    """
    
    try:
        with engine.connect() as conn:
            if 'sqlite' in SQLALCHEMY_DATABASE_URI.lower():
                conn.execute(text(sqlite_sql))
                print("SQLite: product_images表创建成功")
            else:
                conn.execute(text(mysql_sql))
                print("MySQL: product_images表创建成功")
            conn.commit()
    except Exception as e:
        print(f"创建product_images表失败: {str(e)}")

if __name__ == '__main__':
    create_product_images_table()
