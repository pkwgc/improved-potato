#!/usr/bin/env python3
import sqlite3
import json
import os

def check_customer_profiles():
    """检查customer_profiles表中的AI画像数据"""
    db_path = "wechat_system.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customer_profiles'")
        if not cursor.fetchone():
            print("❌ customer_profiles表不存在")
            return
        
        cursor.execute("PRAGMA table_info(customer_profiles)")
        columns = cursor.fetchall()
        print("📊 customer_profiles表结构:")
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
        
        cursor.execute("SELECT COUNT(*) FROM customer_profiles")
        total_count = cursor.fetchone()[0]
        print(f"\n📈 总记录数: {total_count}")
        
        if total_count > 0:
            cursor.execute("""
                SELECT contact_id, profile_type, profile_value, confidence, source, value_level, activity_score, created_at 
                FROM customer_profiles 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            
            records = cursor.fetchall()
            print(f"\n🔍 最新的{len(records)}条记录:")
            
            for i, record in enumerate(records, 1):
                contact_id, profile_type, profile_value, confidence, source, value_level, activity_score, created_at = record
                print(f"\n--- 记录 {i} ---")
                print(f"联系人ID: {contact_id}")
                print(f"画像类型: {profile_type}")
                print(f"置信度: {confidence}")
                print(f"数据源: {source}")
                print(f"价值等级: {value_level}")
                print(f"活跃度分数: {activity_score}")
                print(f"创建时间: {created_at}")
                
                if profile_value:
                    try:
                        data = json.loads(profile_value)
                        print("🎯 AI画像数据:")
                        for key, value in data.items():
                            if isinstance(value, list):
                                print(f"  {key}: {', '.join(map(str, value))}")
                            else:
                                print(f"  {key}: {value}")
                    except json.JSONDecodeError:
                        print(f"  原始数据: {profile_value[:200]}...")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wechat_contacts'")
        if cursor.fetchone():
            print(f"\n👥 检查联系人信息...")
            cursor.execute("""
                SELECT cp.contact_id, wc.nickname, wc.wechat_id, cp.profile_type, cp.created_at
                FROM customer_profiles cp
                LEFT JOIN wechat_contacts wc ON cp.contact_id = wc.id
                ORDER BY cp.created_at DESC
                LIMIT 3
            """)
            
            contact_records = cursor.fetchall()
            for i, record in enumerate(contact_records, 1):
                contact_id, nickname, wechat_id, profile_type, created_at = record
                print(f"  联系人{i}: {nickname or '未知'} ({wechat_id or '无微信ID'}) - {profile_type}")
        else:
            print(f"\n⚠️ 未找到wechat_contacts表，无法显示联系人详细信息")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {str(e)}")

if __name__ == "__main__":
    print("🔍 检查AI画像数据存储...")
    check_customer_profiles()
