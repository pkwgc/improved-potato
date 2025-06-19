import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_implementation():
    """测试标签同步和画像功能实现"""
    print("开始测试实现...")
    
    os.environ['USE_SQLITE'] = 'true'
    
    try:
        from database import get_db, User, WechatContact, CustomerProfile
        import json
        from datetime import datetime
        
        db = next(get_db())
        
        print("✅ 数据库连接成功")
        
        contact = db.query(WechatContact).first()
        if contact is not None:
            if hasattr(contact, 'tags'):
                print("✅ WechatContact.tags字段存在")
            else:
                print("❌ WechatContact.tags字段不存在")
            
            if hasattr(contact, 'require_approval'):
                print("✅ WechatContact.require_approval字段存在")
                print(f"   默认值: {contact.require_approval}")
            else:
                print("❌ WechatContact.require_approval字段不存在")
        else:
            print("⚠️ 数据库中暂无联系人数据")
        
        contacts = db.query(WechatContact).limit(5).all()
        for contact in contacts:
            print(f"\n联系人: {contact.nickname or contact.wechat_id}")
            print(f"  批准设置: {'需要批准' if contact.require_approval else '直接推送'}")
            
            if contact.tags:
                try:
                    tag_list = json.loads(contact.tags)
                    print(f"  标签: {tag_list}")
                except json.JSONDecodeError:
                    print(f"  ❌ 标签解析失败")
            else:
                profile = db.query(CustomerProfile).filter(
                    CustomerProfile.contact_id == contact.id,
                    CustomerProfile.profile_type == "综合画像"
                ).order_by(CustomerProfile.updated_at.desc()).first()
                
                if profile and profile.profile_value:
                    try:
                        profile_data = json.loads(profile.profile_value)
                        labels = profile_data.get("labels", [])
                        if labels:
                            print(f"  从画像同步标签: {labels}")
                        else:
                            print(f"  画像中无标签")
                    except json.JSONDecodeError:
                        print(f"  ❌ 画像数据解析失败")
                else:
                    print(f"  无画像数据")
        
        print("\n✅ 批准设置功能测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    test_implementation()
