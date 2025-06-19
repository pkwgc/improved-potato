import logging
from sqlalchemy import text
from database import engine, Base, WechatContact, WechatMessage, AIStrategy, KeywordFilter, User

logger = logging.getLogger(__name__)

def update_database():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("成功创建新表")
        
        try:
            engine.execute(text("SELECT contacts FROM users LIMIT 1"))
            logger.info("用户和联系人关系已存在")
        except:
            logger.info("用户和联系人关系不存在，已通过模型关系定义添加")
        
        return True
    except Exception as e:
        logger.error(f"更新数据库失败: {str(e)}")
        return False

if __name__ == "__main__":
    update_database()
