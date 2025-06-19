import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import get_db, WechatContact, CustomerProfile, engine
from sqlalchemy import text

def migrate_tags():
    """迁移CustomerProfile中的标签到WechatContact.tags字段"""
    print("开始标签数据迁移...")
    
    try:
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE wechat_contacts ADD COLUMN tags TEXT"))
                print("成功添加tags字段到wechat_contacts表")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("tags字段已存在，跳过添加")
                else:
                    print(f"添加tags字段失败: {e}")
            
            try:
                conn.execute(text("ALTER TABLE wechat_contacts ADD COLUMN require_approval BOOLEAN DEFAULT TRUE"))
                print("成功添加require_approval字段到wechat_contacts表")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("require_approval字段已存在，跳过添加")
                else:
                    print(f"添加require_approval字段失败: {e}")
            
            conn.commit()
    except Exception as e:
        print(f"数据库操作失败: {e}")
        try:
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(wechat_contacts)"))
                columns = [row[1] for row in result.fetchall()]
                print(f"当前表字段: {columns}")
        except Exception as check_e:
            print(f"检查表结构失败: {check_e}")
    
    db = next(get_db())
    try:
        contacts = db.query(WechatContact).all()
        updated_count = 0
        
        for contact in contacts:
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.contact_id == contact.id,
                CustomerProfile.profile_type == "综合画像"
            ).order_by(CustomerProfile.updated_at.desc()).first()
            
            if profile and profile.profile_value:
                try:
                    profile_data = json.loads(profile.profile_value)
                    labels = profile_data.get("labels", [])
                    if labels:
                        contact.tags = json.dumps(labels, ensure_ascii=False)
                        updated_count += 1
                        print(f"同步联系人 {contact.nickname or contact.wechat_id} 的标签: {labels}")
                except json.JSONDecodeError:
                    print(f"解析联系人 {contact.id} 的画像数据失败")
        
        db.commit()
        print(f"标签数据同步完成，共更新 {updated_count} 个联系人")
    except Exception as e:
        print(f"数据同步失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_tags()
