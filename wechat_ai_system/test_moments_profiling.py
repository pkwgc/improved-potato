#!/usr/bin/env python3
"""
朋友圈AI画像分析功能测试脚本
"""

import requests
import json
import time
import hmac
import hashlib
from datetime import datetime

def generate_hmac_signature(app_id, timestamp, nonce, body, app_secret):
    """生成HMAC签名"""
    sign_string = f"{app_id}{timestamp}{nonce}{body}"
    signature = hmac.new(
        app_secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def create_hmac_headers(app_id, app_secret, body_data):
    """创建HMAC认证头部"""
    timestamp = str(int(time.time()))
    nonce = f"test_nonce_{int(time.time())}"
    body_str = json.dumps(body_data, ensure_ascii=False)
    signature = generate_hmac_signature(app_id, timestamp, nonce, body_str, app_secret)
    
    return {
        'Content-Type': 'application/json',
        'X-App-ID': app_id,
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-Signature': signature
    }, body_str

def test_moments_profiling():
    """测试朋友圈AI画像分析"""
    print("测试朋友圈AI画像分析功能...")
    
    test_data = {
        "user_id": "guangwolove",
        "user_wxid": "li258304281314",
        "wechat_id": "pk_wgc",
        "moments": [
            {
                "nickname": "后知后觉、",
                "title": "晒新茶",
                "content": "打了半年的临牌 终于[裂开]",
                "likes": ["桑园村男神涛", "XXXXL先生"],
                "comments": [
                    {"nickname": "不二呀", "content": "不容易"},
                    {"nickname": "LEE", "content": "终于不用各地搞临牌了"}
                ],
                "clicks": 12,
                "user_actions": [
                    {"action": "like", "actor": "自己", "timestamp": "2024-01-15 10:31:00"},
                    {"action": "comment", "actor": "自己", "content": "太美了", "timestamp": "2024-01-15 10:32:00"}
                ]
            },
            {
                "nickname": "后知后觉、",
                "content": "今天去了新开的茶叶店，品尝了几款不错的茶叶，准备买一些送朋友。特别喜欢那款龙井，香气清雅，口感甘甜。",
                "likes": ["茶友小王", "爱茶人", "品茶师傅"],
                "comments": [
                    {"nickname": "茶友小王", "content": "哪家店？推荐一下"},
                    {"nickname": "爱茶人", "content": "我也想去试试"},
                    {"nickname": "品茶师傅", "content": "龙井确实不错，你眼光很好"}
                ],
                "clicks": 15,
                "user_actions": [
                    {"action": "view", "actor": "自己", "timestamp": "2024-01-16 14:20:00"},
                    {"action": "like", "actor": "自己", "timestamp": "2024-01-16 14:21:00"}
                ]
            },
            {
                "nickname": "后知后觉、",
                "content": "周末和朋友们一起去爬山，风景很美，空气清新。运动后喝茶特别香，生活就是要这样慢下来享受。",
                "likes": ["户外达人", "登山爱好者", "茶友小王"],
                "comments": [
                    {"nickname": "户外达人", "content": "哪座山？我们也想去"},
                    {"nickname": "登山爱好者", "content": "运动+品茶，完美组合"}
                ],
                "clicks": 20,
                "user_actions": [
                    {"action": "view", "actor": "自己", "timestamp": "2024-01-17 09:30:00"}
                ]
            }
        ]
    }
    url="http://127.0.0.1:5000/api/initial_sync"
    app_id = "wechat_exe_client"
    app_secret = "wechat_exe_secret_2024"
    headers, body_str = create_hmac_headers(app_id, app_secret, test_data)
    # === 这里打印请求参数 ===
    print(f"请求URL: {url}")
    print("请求headers:")
    print(json.dumps(headers, indent=2, ensure_ascii=False))
    print("请求body:")
    print(body_str)
    try:
        print("发送请求到 /api/initial_sync...")
        response = requests.post(
            url,
            headers=headers,
            #data=body_str,
			data=body_str.encode('utf-8'),  # <=== 这里
            timeout=30
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                profile = result.get("profile", {})
                print("\n=== AI画像分析结果 ===")
                print(f"用户画像摘要: {profile.get('summary', '')}")
                print(f"用户标签: {profile.get('labels', [])}")
                print(f"客户分类: {profile.get('category', '')}")
                print(f"兴趣爱好: {profile.get('hobbies', [])}")
                print("=== 测试成功 ===")
            else:
                print(f"API返回失败: {result}")
        else:
            print(f"请求失败: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == "__main__":
    test_moments_profiling()
