import requests
import json
import hmac
import hashlib
import time

def test_initial_sync():
    """测试朋友圈AI画像分析接口"""
    
    test_data = {
        "user_id": "test_user_001",
        "user_wxid": "wxid_test001",
        "wechat_id": "wxid_friend001",
        "moments": [
            {
                "nickname": "测试好友",
                "title": "今天的美食",
                "content": "今天尝试了新的日料店，味道很不错！推荐给大家",
                "likes": ["friend1", "friend2"],
                "comments": [{"user": "friend1", "content": "看起来很好吃"}],
                "clicks": 15,
                "user_actions": ["like", "comment"]
            },
            {
                "nickname": "测试好友",
                "title": "周末旅行",
                "content": "周末去了杭州西湖，风景真美！",
                "likes": ["friend3", "friend4"],
                "comments": [],
                "clicks": 8,
                "user_actions": ["like"]
            }
        ]
    }
    
    timestamp = str(int(time.time()))
    
    try:
        response = requests.post(
            "http://localhost:5000/api/initial_sync",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        
        if response.status_code == 200:
            print("✅ AI画像分析接口测试成功")
        else:
            print("❌ AI画像分析接口测试失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

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
