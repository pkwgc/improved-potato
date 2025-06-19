import os
import sys
from sqlalchemy import text
from database import get_db, engine

def add_websocket_columns():
    """添加WebSocket增强功能所需的数据库字段"""
    db = next(get_db())
    
    try:
        print("正在添加WebSocket增强功能的数据库字段...")
        
        try:
            db.execute(text("ALTER TABLE wechat_messages ADD COLUMN message_id VARCHAR(255) UNIQUE"))
            print("✓ 已添加 wechat_messages.message_id 字段")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("✓ wechat_messages.message_id 字段已存在")
            else:
                print(f"✗ 添加 wechat_messages.message_id 字段失败: {e}")
        
        try:
            db.execute(text("ALTER TABLE wechat_messages ADD COLUMN ack_status VARCHAR(20) DEFAULT 'pending'"))
            print("✓ 已添加 wechat_messages.ack_status 字段")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("✓ wechat_messages.ack_status 字段已存在")
            else:
                print(f"✗ 添加 wechat_messages.ack_status 字段失败: {e}")
        
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN last_ack_id VARCHAR(255)"))
            print("✓ 已添加 users.last_ack_id 字段")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("✓ users.last_ack_id 字段已存在")
            else:
                print(f"✗ 添加 users.last_ack_id 字段失败: {e}")
        
        db.commit()
        print("\n✅ WebSocket增强功能数据库字段添加完成！")
        
    except Exception as e:
        print(f"\n❌ 数据库字段添加失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_websocket_columns()
