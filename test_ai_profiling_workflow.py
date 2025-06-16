import requests
import json
import hmac
import hashlib
import time
import uuid
import os

def generate_hmac_signature(app_id, timestamp, nonce, body, app_secret):
    """生成HMAC签名"""
    sign_string = f"{app_id}{timestamp}{nonce}{body}"
    signature = hmac.new(
        app_secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def test_initial_sync():
    """测试朋友圈AI画像分析接口"""
    
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
    
    app_id = os.getenv("TEST_APP_ID", "wechat_exe_client")
    app_secret = os.getenv("TEST_APP_SECRET")
    
    if not app_secret:
        print("❌ 请设置环境变量 TEST_APP_SECRET")
        print("   export TEST_APP_SECRET=your_actual_secret")
        return False
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
    
    print(f"🔐 认证信息:")
    print(f"  App ID: {app_id}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Nonce: {nonce[:8]}...")
    print(f"  Signature: {signature[:16]}...")
    print(f"  Body length: {len(body_str)} chars, {len(body_bytes)} bytes")
    
    try:
        response = requests.post(
            "http://localhost:5000/api/initial_sync",
            data=body_bytes,
            headers=headers,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            print("✅ AI画像分析接口测试成功")
            return True
        else:
            try:
                error_result = response.json()
                print(f"错误响应: {json.dumps(error_result, ensure_ascii=False, indent=2)}")
            except:
                print(f"错误响应: {response.text}")
            print("❌ AI画像分析接口测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def test_profile_update():
    """测试画像更新接口"""
    
    test_data = {
        "user_id": "test_user_001",
        "profile_data": {
            "interests": ["美食", "旅行"],
            "tags": ["活跃用户", "生活品质"],
            "category": "高价值客户",
            "summary": "喜欢美食和旅行的活跃用户"
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/api/profile_update",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"画像更新状态码: {response.status_code}")
        print(f"画像更新响应: {response.json()}")
        
        if response.status_code == 200:
            print("✅ 画像更新接口测试成功")
        else:
            print("❌ 画像更新接口测试失败")
            
    except Exception as e:
        print(f"❌ 画像更新测试失败: {str(e)}")

if __name__ == "__main__":
    print("开始测试微信朋友圈AI画像系统...")
    print("=" * 50)
    
    print("1. 测试朋友圈AI画像分析接口")
    test_initial_sync()
    
    print("\n2. 测试画像更新接口")
    test_profile_update()
    
    print("\n测试完成！")
