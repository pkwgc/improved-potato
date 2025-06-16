#!/usr/bin/env python3
"""
微信朋友圈AI画像系统测试脚本 - 修复版
使用正确的HMAC认证参数测试 /api/initial_sync 接口
"""

import requests
import json
import hmac
import hashlib
import time
import uuid
import os

def generate_hmac_signature(app_id, timestamp, nonce, body, app_secret):
    """生成HMAC签名 - 与服务器端完全一致的实现"""
    if isinstance(body, bytes):
        body_str = body.decode('utf-8')
    else:
        body_str = str(body)
    
    sign_string = f"{app_id}{timestamp}{nonce}{body_str}"
    signature = hmac.new(
        app_secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def test_initial_sync_with_correct_auth():
    """使用正确的HMAC认证测试朋友圈AI画像分析接口"""
    
    test_data = {
        "user_id": "test_user_001",
        "user_wxid": "wxid_test001", 
        "wechat_id": "wxid_friend001",
        "moments": [
            {
                "nickname": "张小美",
                "title": "今天的美食",
                "content": "今天尝试了新的日料店，味道很不错！推荐给大家。特别是他们家的三文鱼刺身，新鲜度满分！",
                "likes": ["friend1", "friend2", "friend3"],
                "comments": [
                    {"user": "friend1", "content": "看起来很好吃，在哪里？"},
                    {"user": "friend2", "content": "我也想去试试！"}
                ],
                "clicks": 25,
                "user_actions": ["like", "comment"]
            },
            {
                "nickname": "张小美", 
                "title": "周末旅行",
                "content": "周末去了杭州西湖，风景真美！断桥残雪虽然没有雪，但是湖光山色依然让人心旷神怡。还去了河坊街吃了很多小吃。",
                "likes": ["friend3", "friend4", "friend5"],
                "comments": [
                    {"user": "friend4", "content": "杭州确实很美，我上次去也很喜欢"}
                ],
                "clicks": 18,
                "user_actions": ["like"]
            },
            {
                "nickname": "张小美",
                "title": "新买的相机", 
                "content": "终于入手了心仪已久的佳能R5！试拍了几张，画质真的没话说。准备这个周末去公园拍拍花花草草。",
                "likes": ["friend1", "friend6"],
                "comments": [
                    {"user": "friend6", "content": "哇，专业设备！期待你的作品"}
                ],
                "clicks": 22,
                "user_actions": ["like", "comment"]
            }
        ]
    }
    
    app_id = "wechat_exe_client"
    app_secret = "wechat_exe_secret_2024"
    
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    
    body_str = json.dumps(test_data, separators=(',', ':'), ensure_ascii=False)
    body_bytes = body_str.encode('utf-8')
    
    signature = generate_hmac_signature(app_id, timestamp, nonce, body_str, app_secret)
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-App-ID": app_id,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature
    }
    
    print("🔐 HMAC认证信息:")
    print(f"  App ID: {app_id}")
    print(f"  App Secret: {app_secret[:8]}...{app_secret[-4:]}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Nonce: {nonce[:8]}...")
    print(f"  Signature: {signature[:16]}...")
    print(f"  Body length: {len(body_str)} chars, {len(body_bytes)} bytes")
    print()
    
    try:
        print("📤 发送AI画像分析请求...")
        response = requests.post(
            "http://localhost:5000/api/initial_sync",
            data=body_bytes,
            headers=headers,
            timeout=30
        )
        
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
                print("🎉 AI画像分析接口测试成功！")
                return True
            except json.JSONDecodeError:
                print(f"✅ 响应内容: {response.text}")
                print("🎉 AI画像分析接口测试成功！")
                return True
        else:
            try:
                error_result = response.json()
                print(f"❌ 错误响应: {json.dumps(error_result, ensure_ascii=False, indent=2)}")
            except:
                print(f"❌ 错误响应: {response.text}")
            print("❌ AI画像分析接口测试失败")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败：请确保系统已启动")
        print("   启动命令: export USE_SQLITE=true && python app.py")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def check_system_status():
    """检查系统状态"""
    print("🔍 检查系统状态...")
    
    try:
        response = requests.get("http://localhost:5000/admin", timeout=5)
        if response.status_code in [200, 302]:
            print("✅ Flask应用已启动")
            return True
        else:
            print(f"⚠️ Flask应用响应异常，状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Flask应用未启动")
        print("   请运行: export USE_SQLITE=true && python app.py")
        return False
    except Exception as e:
        print(f"❌ 检查Flask应用状态失败: {str(e)}")
        return False

def check_database():
    """检查数据库中的AI画像数据"""
    import sqlite3
    import os
    
    db_files = ['wechat_system.db', 'chatbot.db']
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"📊 找到数据库文件: {db_file}")
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%profile%'")
                profile_tables = cursor.fetchall()
                
                if profile_tables:
                    for table in profile_tables:
                        table_name = table[0]
                        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                        count = cursor.fetchone()[0]
                        print(f"   {table_name}表中有 {count} 条记录")
                        
                        if count > 0:
                            cursor.execute(f'SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 1')
                            latest = cursor.fetchone()
                            print(f"   最新记录: {latest}")
                else:
                    print("   未找到画像相关表")
                
                conn.close()
                return True
                
            except Exception as e:
                print(f"❌ 数据库检查失败: {str(e)}")
                return False
    
    print("❌ 未找到数据库文件")
    print("   数据库文件应该在系统启动后自动创建")
    return False

def create_startup_script():
    """创建启动脚本"""
    startup_script_sh = """#!/bin/bash

echo "🚀 启动微信朋友圈AI画像系统..."

export USE_SQLITE=true

echo "📦 检查依赖包..."
pip install -r requirements.txt

echo "🔥 启动Flask应用..."
python app.py
"""
    
    startup_script_bat = """@echo off
REM 微信朋友圈AI画像系统启动脚本

echo 🚀 启动微信朋友圈AI画像系统...

REM 设置SQLite模式
set USE_SQLITE=true

REM 检查Python依赖
echo 📦 检查依赖包...
pip install -r requirements.txt

REM 启动Flask应用
echo 🔥 启动Flask应用...
python app.py
"""
    
    with open('start_system.sh', 'w', encoding='utf-8') as f:
        f.write(startup_script_sh)
    
    with open('start_system.bat', 'w', encoding='utf-8') as f:
        f.write(startup_script_bat)
    
    os.chmod('start_system.sh', 0o755)
    print("✅ 已创建启动脚本: start_system.sh (Linux/Mac) 和 start_system.bat (Windows)")

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 微信朋友圈AI画像系统测试 - 修复版")
    print("=" * 60)
    
    print("\n1️⃣ 检查系统状态")
    print("-" * 40)
    system_ok = check_system_status()
    
    if not system_ok:
        print("\n💡 系统未启动，创建启动脚本...")
        create_startup_script()
        print("\n请先启动系统:")
        print("  Linux/Mac: ./start_system.sh")
        print("  Windows: start_system.bat")
        print("  手动启动: export USE_SQLITE=true && python app.py")
        print("\n然后重新运行此测试脚本")
        exit(1)
    
    print("\n2️⃣ 测试AI画像分析接口（正确HMAC认证）")
    print("-" * 40)
    success = test_initial_sync_with_correct_auth()
    
    print("\n3️⃣ 检查数据库中的画像数据")
    print("-" * 40)
    db_ok = check_database()
    
    print("\n" + "=" * 60)
    print("📋 测试结果总结")
    print("=" * 60)
    print(f"系统状态: {'✅ 正常' if system_ok else '❌ 异常'}")
    print(f"HMAC认证测试: {'✅ 通过' if success else '❌ 失败'}")
    print(f"数据库检查: {'✅ 通过' if db_ok else '❌ 失败'}")
    
    if success and db_ok:
        print("\n🎉 AI画像系统测试完全成功！")
        print("💡 建议：登录管理后台查看生成的画像数据")
        print("   访问: http://localhost:5000/admin")
        print("   用户名: admin, 密码: admin123")
    else:
        print("\n⚠️ 测试未完全通过")
        if not success:
            print("   - HMAC认证失败，请检查密钥配置")
        if not db_ok:
            print("   - 数据库问题，请检查系统启动状态")
