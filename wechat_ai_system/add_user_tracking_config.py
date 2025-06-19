import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import engine, SessionLocal
import logging

logger = logging.getLogger(__name__)

def migrate_user_tracking_config():
    """添加用户跟踪配置表和相关字段"""
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_tracking_configs (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    user_id INTEGER NOT NULL,
                    customer_type VARCHAR(20) NOT NULL,
                    tracking_cycle_days INTEGER DEFAULT 90,
                    tracking_periods INTEGER DEFAULT 3,
                    period_duration_days INTEGER DEFAULT 30,
                    max_contacts_per_period INTEGER DEFAULT 2,
                    contact_interval_days INTEGER DEFAULT 7,
                    silence_threshold_periods INTEGER DEFAULT 3,
                    auto_tracking_enabled BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE KEY unique_user_customer_type (user_id, customer_type)
                )
            """))
            
            try:
                conn.execute(text("ALTER TABLE wechat_contacts ADD COLUMN tracking_start_date DATETIME"))
            except:
                pass
            try:
                conn.execute(text("ALTER TABLE wechat_contacts ADD COLUMN current_period INTEGER DEFAULT 1"))
            except:
                pass
            try:
                conn.execute(text("ALTER TABLE wechat_contacts ADD COLUMN period_contact_count INTEGER DEFAULT 0"))
            except:
                pass
            try:
                conn.execute(text("ALTER TABLE wechat_contacts ADD COLUMN silence_period_count INTEGER DEFAULT 0"))
            except:
                pass
            try:
                conn.execute(text("ALTER TABLE wechat_contacts ADD COLUMN is_silenced BOOLEAN DEFAULT FALSE"))
            except:
                pass
            
            logger.info("用户跟踪配置迁移完成")
            
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_user_tracking_config()
