"""
数据库迁移脚本 - 添加缺失的列
"""

import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# ==== 直接在脚本中定义数据库连接信息 ====
username = 'pkwgc'
password = quote_plus('Wghfd@584521@fd')  # 自动编码特殊字符，比如 @ -> %40
host = 'rm-m5e0666vtv5234qi39o.mysql.rds.aliyuncs.com'
port = 3306
database = 'chatbot'


SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
# ===================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_missing_columns():
    """添加缺失的数据库列"""
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URI)
        conn = engine.connect()
        
        try:
            conn.execute(text("SELECT original_filename FROM inventory_uploads LIMIT 1"))
            logger.info("original_filename列已存在，无需添加")
        except Exception as e:
            if "original_filename" in str(e):
                logger.info("添加original_filename列到inventory_uploads表")
                conn.execute(text("ALTER TABLE inventory_uploads ADD COLUMN original_filename VARCHAR(255)"))
                logger.info("成功添加original_filename列")
            else:
                logger.error(f"检查original_filename列时出错: {str(e)}")
        
        try:
            conn.execute(text("SELECT upload_time FROM inventory_uploads LIMIT 1"))
            logger.info("upload_time列已存在，无需添加")
        except Exception as e:
            if "upload_time" in str(e):
                logger.info("添加upload_time列到inventory_uploads表")
                conn.execute(text("ALTER TABLE inventory_uploads ADD COLUMN upload_time DATETIME"))
                logger.info("成功添加upload_time列")
            else:
                logger.error(f"检查upload_time列时出错: {str(e)}")
        
        try:
            conn.execute(text("SELECT * FROM token_package_purchases LIMIT 1"))
            logger.info("token_package_purchases表已存在")
        except Exception as e:
            if "doesn't exist" in str(e) or "does not exist" in str(e):
                logger.info("创建token_package_purchases表")
                conn.execute(text("""
                CREATE TABLE token_package_purchases (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    package_id INT,
                    purchase_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    token_amount INT DEFAULT 0,
                    price FLOAT DEFAULT 0.0,
                    status VARCHAR(20) DEFAULT 'pending',
                    payment_method VARCHAR(50),
                    transaction_id VARCHAR(100),
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (package_id) REFERENCES token_packages(id)
                )
                """))
                logger.info("成功创建token_package_purchases表")
            else:
                logger.error(f"检查token_package_purchases表时出错: {str(e)}")
        
        conn.close()
        logger.info("数据库迁移完成")
        return True
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        return False

if __name__ == "__main__":
    add_missing_columns()
