#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db, WechatContact, UserTrackingConfig, User

def debug_tracking_issue():
    """调试手动跟踪失败的问题"""
    print("调试手动跟踪问题...")
    
    db = next(get_db())
    try:
        contact_id = 1141
        contact = db.query(WechatContact).filter(WechatContact.id == contact_id).first()
        
        if contact:
            print(f'联系人 {contact.id}:')
            print(f'  - auto_follow_enabled: {contact.auto_follow_enabled}')
            print(f'  - follow_disabled_by_user: {contact.follow_disabled_by_user}')
            print(f'  - customer_type: {contact.customer_type}')
            print(f'  - owner_id: {contact.owner_id}')
            print(f'  - nickname: {contact.nickname}')
            print(f'  - wechat_id: {contact.wechat_id}')
            
            user_config = db.query(UserTrackingConfig).filter(
                UserTrackingConfig.user_id == contact.owner_id,
                UserTrackingConfig.customer_type == contact.customer_type
            ).first()
            
            if user_config:
                print(f'找到用户跟踪配置:')
                print(f'  - auto_tracking_enabled: {user_config.auto_tracking_enabled}')
                print(f'  - tracking_cycle_days: {user_config.tracking_cycle_days}')
                print(f'  - contact_interval_days: {user_config.contact_interval_days}')
            else:
                print(f'未找到用户跟踪配置 (user_id={contact.owner_id}, customer_type={contact.customer_type})')
                
            all_configs = db.query(UserTrackingConfig).filter(
                UserTrackingConfig.user_id == contact.owner_id
            ).all()
            print(f'用户 {contact.owner_id} 的所有跟踪配置: {len(all_configs)} 个')
            for config in all_configs:
                print(f'  - {config.customer_type}: enabled={config.auto_tracking_enabled}')
                
            user = db.query(User).filter(User.id == contact.owner_id).first()
            if user:
                print(f'用户信息: user_id={user.user_id}, username={user.username}')
            else:
                print(f'未找到用户 ID {contact.owner_id}')
                
        else:
            print(f'未找到联系人 ID {contact_id}')
            
    except Exception as e:
        print(f"调试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_tracking_issue()
