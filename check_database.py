#!/usr/bin/env python3
import sqlite3
import json
import sys
import os

def check_database():
    """检查数据库中的AI画像数据"""
    db_path = 'wechat_system.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== 数据库中的所有表 ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        if tables:
            for table in tables:
                print(f"  表名: {table[0]}")
        else:
            print("数据库中没有表")
        print()
        
        profile_tables = [t[0] for t in tables if 'profile' in t[0].lower()]
        customer_tables = [t[0] for t in tables if 'customer' in t[0].lower()]
        
        print("=== Profile相关表数据 ===")
        for table_name in profile_tables + customer_tables:
            print(f"--- {table_name} 表 ---")
            try:
                cursor.execute(f'SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 3')
                rows = cursor.fetchall()
                if rows:
                    cursor.execute(f'PRAGMA table_info({table_name})')
                    columns = [col[1] for col in cursor.fetchall()]
                    print(f"列名: {columns}")
                    for i, row in enumerate(rows, 1):
                        row_dict = dict(zip(columns, row))
                        print(f"记录 {i}: {row_dict}")
                else:
                    print("暂无数据")
            except Exception as e:
                print(f"查询失败: {e}")
            print()
        
        if not profile_tables and not customer_tables:
            print("=== CustomerProfile 表数据 ===")
            cursor.execute('SELECT * FROM customer_profile ORDER BY created_at DESC LIMIT 5')
            profiles = cursor.fetchall()
        
        if profiles:
            cursor.execute('PRAGMA table_info(customer_profile)')
            columns = [col[1] for col in cursor.fetchall()]
            print(f"列名: {columns}")
            print()
            
            for i, profile in enumerate(profiles, 1):
                profile_dict = dict(zip(columns, profile))
                print(f"记录 {i}:")
                for key, value in profile_dict.items():
                    if key == 'profile_data' and value:
                        try:
                            parsed_data = json.loads(value)
                            print(f"  {key}: {json.dumps(parsed_data, ensure_ascii=False, indent=4)}")
                        except:
                            print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: {value}")
                print("-" * 50)
        else:
            print("暂无CustomerProfile数据")
        
        print("\n=== Moment 表数据 ===")
        cursor.execute('SELECT * FROM moment ORDER BY created_at DESC LIMIT 3')
        moments = cursor.fetchall()
        
        if moments:
            cursor.execute('PRAGMA table_info(moment)')
            columns = [col[1] for col in cursor.fetchall()]
            print(f"列名: {columns}")
            print()
            
            for i, moment in enumerate(moments, 1):
                moment_dict = dict(zip(columns, moment))
                print(f"朋友圈记录 {i}:")
                for key, value in moment_dict.items():
                    if key == 'content' and value and len(str(value)) > 100:
                        print(f"  {key}: {str(value)[:100]}...")
                    else:
                        print(f"  {key}: {value}")
                print("-" * 30)
        else:
            print("暂无Moment数据")
        
        print("\n=== AIStrategy 表数据 ===")
        cursor.execute('SELECT name, description, created_at FROM ai_strategy ORDER BY created_at DESC LIMIT 3')
        strategies = cursor.fetchall()
        
        if strategies:
            print("AI策略:")
            for strategy in strategies:
                print(f"  名称: {strategy[0]}, 描述: {strategy[1]}, 创建时间: {strategy[2]}")
        else:
            print("暂无AI策略数据")
        
        conn.close()
        print("\n✅ 数据库检查完成")
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {str(e)}")

if __name__ == "__main__":
    check_database()
