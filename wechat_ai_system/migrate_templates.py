from database import get_db, Template, create_tables
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)



def migrate_database():
    """迁移数据库，添加template_type字段"""
    db = next(get_db())
    try:
        try:
            db.execute(text("ALTER TABLE templates ADD COLUMN template_type VARCHAR(20) DEFAULT 'chat' NOT NULL"))
            db.commit()
            logger.info("成功添加template_type字段")
        except Exception as e:
            if "Duplicate column name" in str(e) or "already exists" in str(e):
                logger.info("template_type字段已存在，跳过添加")
            else:
                raise e

        logger.info("数据库迁移完成 - 请通过后台管理界面创建所需的模板")
            
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_database()
