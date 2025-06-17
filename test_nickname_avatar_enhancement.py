#!/usr/bin/env python3
import json
import requests
import hashlib
import hmac
import time
from datetime import datetime

def create_hmac_headers(app_id, app_secret, data):
    body_str = json.dumps(data, ensure_ascii=False)
    timestamp = str(int(time.time()))
    nonce = "test_nonce_12345"
    
    string_to_sign = f"{app_id}{timestamp}{nonce}{body_str}"
    signature = hmac.new(
        app_secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'Content-Type': 'application/json',
        'X-App-Id': app_id,
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-Signature': signature
    }
    
    return headers, body_str

def test_backward_compatibility():
    """测试向后兼容性 - 不包含新字段的原有请求格式"""
    print("=== 测试向后兼容性（不包含nickname和avatar_style字段）===")
    
    test_data = {
        "user_id": "guangwolove",
        "user_wxid": "li258304281314",
        "wechat_id": "pk_wgc",
        "moments": [
            {
                "title": "晒新茶",
                "content": "打了半年的临牌 终于[裂开]",
                "likes": ["friend1", "friend2"],
                "comments": [
                    {"user": "friend1", "content": "恭喜恭喜！"},
                    {"user": "friend2", "content": "终于等到了"}
                ],
                "user_actions": ["点赞", "评论"]
            }
        ]
    }
    
    url = "http://127.0.0.1:5000/api/initial_sync"
    app_id = "wechat_exe_client"
    app_secret = "wechat_exe_secret_2024"
    
    headers, body_str = create_hmac_headers(app_id, app_secret, test_data)
    
    try:
        print("发送请求（不包含新字段）...")
        response = requests.post(url, headers=headers, data=body_str, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 向后兼容性测试通过")
                return True
            else:
                print("❌ 向后兼容性测试失败 - API返回失败")
                return False
        else:
            print("❌ 向后兼容性测试失败 - HTTP状态码错误")
            return False
            
    except Exception as e:
        print(f"❌ 向后兼容性测试失败 - 异常: {str(e)}")
        return False

def test_new_fields():
    """测试新字段功能 - 包含nickname和avatar_style字段"""
    print("\n=== 测试新字段功能（包含nickname和avatar_style字段）===")
    
    test_data = {
        "user_id": "guangwolove",
        "user_wxid": "li258304281314", 
        "wechat_id": "pk_wgc",
        "nickname": "后知后觉、",
        "avatar_style": "https://wx.qlogo.cn/mmhead/ver_1/rjNLVztbvVVvzUMKeqEeP5bFKsxeIpTckU9BMNrTGCpAelSiam6icOCmqFtIiaZrrBfFCjnMWP90jA9KvcGYIQPDdMnk661PGcibibtlzldzJg4EmO7M0U5dp3LD3ka9HE72T/132",
        "moments": [
            {
                "title": "晒新茶",
                "content": "打了半年的临牌 终于[裂开]",
                "likes": ["friend1", "friend2"],
                "comments": [
                    {"user": "friend1", "content": "恭喜恭喜！"},
                    {"user": "friend2", "content": "终于等到了"}
                ],
                "user_actions": ["点赞", "评论"]
            },
            {
                "title": "周末爬山",
                "content": "今天天气不错，和朋友们一起爬山，心情很好！",
                "likes": ["friend3", "friend4", "friend5"],
                "comments": [
                    {"user": "friend3", "content": "风景真美！"},
                    {"user": "friend4", "content": "下次带我一起"}
                ],
                "user_actions": ["点赞", "分享"]
            }
        ]
    }
    
    url = "http://127.0.0.1:5000/api/initial_sync"
    app_id = "wechat_exe_client"
    app_secret = "wechat_exe_secret_2024"
    
    headers, body_str = create_hmac_headers(app_id, app_secret, test_data)
    
    try:
        print("发送请求（包含新字段）...")
        response = requests.post(url, headers=headers, data=body_str, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                profile = result.get("profile", {})
                print("✅ 新字段功能测试通过")
                print(f"生成的画像摘要: {profile.get('summary', 'N/A')}")
                print(f"用户标签: {profile.get('labels', [])}")
                print(f"客户分类: {profile.get('category', 'N/A')}")
                print(f"兴趣爱好: {profile.get('hobbies', [])}")
                return True
            else:
                print("❌ 新字段功能测试失败 - API返回失败")
                return False
        else:
            print("❌ 新字段功能测试失败 - HTTP状态码错误")
            return False
            
    except Exception as e:
        print(f"❌ 新字段功能测试失败 - 异常: {str(e)}")
        return False

def main():
    print("开始测试朋友圈AI画像分析接口的nickname和avatar_style字段增强功能")
    print("=" * 80)
    
    backward_compatible = test_backward_compatibility()
    
    new_fields_working = test_new_fields()
    
    print("\n" + "=" * 80)
    print("测试结果汇总:")
    print(f"向后兼容性: {'✅ 通过' if backward_compatible else '❌ 失败'}")
    print(f"新字段功能: {'✅ 通过' if new_fields_working else '❌ 失败'}")
    
    if backward_compatible and new_fields_working:
        print("\n🎉 所有测试通过！nickname和avatar_style字段增强功能实现成功！")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查实现")
        return False

if __name__ == "__main__":
    main()
