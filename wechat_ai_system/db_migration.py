import os
import sys
from sqlalchemy import create_engine, text, inspect
import config

def migrate_database():
    """执行数据库迁移，添加新字段到wechat_contacts表"""
    print("开始数据库迁移...")
    
    use_sqlite = os.environ.get('USE_SQLITE', 'false').lower() == 'true'
    
    if use_sqlite:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_system.db')
        engine = create_engine(f'sqlite:///{db_path}')
    else:
        try:
            engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
        except Exception as e:
            print(f"数据库连接失败: {str(e)}")
            print("尝试使用SQLite作为备用数据库...")
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_system.db')
            engine = create_engine(f'sqlite:///{db_path}')
    
    try:
        conn = engine.connect()
        inspector = inspect(engine)
        
        if 'wechat_contacts' not in inspector.get_table_names():
            print("wechat_contacts表不存在，请先创建表结构")
            return False
        
        columns = [c['name'] for c in inspector.get_columns('wechat_contacts')]
        
        if 'last_active_at' not in columns:
            print("添加last_active_at字段...")
            if engine.name == 'sqlite':
                add_last_active_at = text("""
                    ALTER TABLE wechat_contacts 
                    ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
            else:
                add_last_active_at = text("""
                    ALTER TABLE wechat_contacts 
                    ADD COLUMN last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP
                """)
            conn.execute(add_last_active_at)
            print("last_active_at字段添加成功")
        else:
            print("last_active_at字段已存在")
        
        if 'unread_count' not in columns:
            print("添加unread_count字段...")
            add_unread_count = text("""
                ALTER TABLE wechat_contacts 
                ADD COLUMN unread_count INTEGER DEFAULT 0
            """)
            conn.execute(add_unread_count)
            print("unread_count字段添加成功")
        else:
            print("unread_count字段已存在")
        
        conn.commit()
        conn.close()
        print("数据库迁移完成")
        return True
    except Exception as e:
        print(f"数据库迁移失败: {str(e)}")
        return False

if __name__ == "__main__":
    migrate_database()
