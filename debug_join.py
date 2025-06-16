#!/usr/bin/env python3
import sqlite3
import json
import os

def debug_database_join():
    """调试数据库连接问题"""
    db_path = "wechat_system.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 检查customer_profiles表...")
        cursor.execute("SELECT contact_id, profile_type, value_level, activity_score FROM customer_profiles")
        profiles = cursor.fetchall()
        print(f"customer_profiles记录数: {len(profiles)}")
        for profile in profiles:
            print(f"  contact_id={profile[0]}, profile_type={profile[1]}, value_level={profile[2]}, activity_score={profile[3]}")
        
        print("\n🔍 检查wechat_contacts表...")
        cursor.execute("SELECT id, wechat_id, nickname, remark FROM wechat_contacts")
        contacts = cursor.fetchall()
        print(f"wechat_contacts记录数: {len(contacts)}")
        for contact in contacts:
            print(f"  id={contact[0]}, wechat_id={contact[1]}, nickname={contact[2]}, remark={contact[3]}")
        
        print("\n🔍 测试JOIN查询...")
        cursor.execute("""
            SELECT cp.contact_id, cp.profile_type, cp.value_level, cp.activity_score,
                   wc.wechat_id, wc.nickname, wc.remark
            FROM customer_profiles cp
            JOIN wechat_contacts wc ON cp.contact_id = wc.id
        """)
        
        join_results = cursor.fetchall()
        print(f"JOIN查询结果数: {len(join_results)}")
        for result in join_results:
            print(f"  联系人ID={result[0]}, 微信ID={result[4]}, 昵称={result[5]}, 备注={result[6]}")
        
        if len(join_results) == 0:
            print("\n❌ JOIN查询无结果，检查是否有孤立记录...")
            cursor.execute("SELECT contact_id FROM customer_profiles WHERE contact_id NOT IN (SELECT id FROM wechat_contacts)")
            orphaned = cursor.fetchall()
            if orphaned:
                print(f"发现孤立的customer_profiles记录，contact_id: {[r[0] for r in orphaned]}")
            else:
                print("未发现孤立记录")
        
        print("\n🔍 检查所有表...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("数据库中的表:")
        for table in tables:
            print(f"  {table[0]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库调试失败: {str(e)}")

if __name__ == "__main__":
    debug_database_join()
