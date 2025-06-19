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
                SELECT user_id, wechat_id, profile_type, profile_data, created_at 
                FROM customer_profiles 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            
            records = cursor.fetchall()
            print(f"\n🔍 最新的{len(records)}条记录:")
            
            for i, record in enumerate(records, 1):
                user_id, wechat_id, profile_type, profile_data, created_at = record
                print(f"\n--- 记录 {i} ---")
                print(f"用户ID: {user_id}")
                print(f"微信ID: {wechat_id}")
                print(f"画像类型: {profile_type}")
                print(f"创建时间: {created_at}")
                
                if profile_data:
                    try:
                        data = json.loads(profile_data)
                        print("画像数据:")
                        for key, value in data.items():
                            if isinstance(value, list):
                                print(f"  {key}: {', '.join(value)}")
                            else:
                                print(f"  {key}: {value}")
                    except json.JSONDecodeError:
                        print(f"  原始数据: {profile_data[:200]}...")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {str(e)}")

if __name__ == "__main__":
    print("🔍 检查AI画像数据存储...")
    check_customer_profiles()
