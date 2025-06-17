#!/usr/bin/env python3
"""
朋友圈AI画像分析接口增强功能测试脚本
测试nickname和avatar_style字段的完整功能
"""
import json
import requests
import hashlib
import hmac
import time
from datetime import datetime

def create_hmac_headers(app_id, app_secret, data):
    """创建HMAC签名头部"""
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
    print("=== 测试1: 向后兼容性（不包含nickname和avatar_style字段）===")
    
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
    
    url = "http://127.0.0.1:5001/api/initial_sync"
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
                profile = result.get("profile", {})
                print(f"生成的画像摘要: {profile.get('summary', 'N/A')}")
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

def test_nickname_only():
    """测试仅包含nickname字段"""
    print("\n=== 测试2: 仅包含nickname字段 ===")
    
    test_data = {
        "user_id": "guangwolove",
        "user_wxid": "li258304281314", 
        "wechat_id": "pk_wgc",
        "nickname": "后知后觉、",
        "moments": [
            {
                "title": "周末爬山",
                "content": "今天天气不错，和朋友们一起爬山，心情很好！🏔️",
                "likes": ["friend3", "friend4", "friend5"],
                "comments": [
                    {"user": "friend3", "content": "风景真美！"},
                    {"user": "friend4", "content": "下次带我一起"}
                ],
                "user_actions": ["点赞", "分享"]
            }
        ]
    }
    
    url = "http://127.0.0.1:5001/api/initial_sync"
    app_id = "wechat_exe_client"
    app_secret = "wechat_exe_secret_2024"
    
    headers, body_str = create_hmac_headers(app_id, app_secret, test_data)
    
    try:
        print("发送请求（仅包含nickname）...")
        response = requests.post(url, headers=headers, data=body_str, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ nickname字段测试通过")
                profile = result.get("profile", {})
                print(f"生成的画像摘要: {profile.get('summary', 'N/A')}")
                print(f"用户标签: {profile.get('labels', [])}")
                return True
            else:
                print("❌ nickname字段测试失败 - API返回失败")
                return False
        else:
            print("❌ nickname字段测试失败 - HTTP状态码错误")
            return False
            
    except Exception as e:
        print(f"❌ nickname字段测试失败 - 异常: {str(e)}")
        return False

def test_avatar_style_only():
    """测试仅包含avatar_style字段"""
    print("\n=== 测试3: 仅包含avatar_style字段 ===")
    
    test_data = {
        "user_id": "guangwolove",
        "user_wxid": "li258304281314", 
        "wechat_id": "pk_wgc",
        "avatar_style": "https://wx.qlogo.cn/mmhead/ver_1/rjNLVztbvVVvzUMKeqEeP5bFKsxeIpTckU9BMNrTGCpAelSiam6icOCmqFtIiaZrrBfFCjnMWP90jA9KvcGYIQPDdMnk661PGcibibtlzldzJg4EmO7M0U5dp3LD3ka9HE72T/132",
        "moments": [
            {
                "title": "美食分享",
                "content": "今天尝试了新的餐厅，味道不错！推荐给大家 👍",
                "likes": ["friend6", "friend7"],
                "comments": [
                    {"user": "friend6", "content": "看起来很好吃"},
                    {"user": "friend7", "content": "在哪里？"}
                ],
                "user_actions": ["点赞"]
            }
        ]
    }
    
    url = "http://127.0.0.1:5001/api/initial_sync"
    app_id = "wechat_exe_client"
    app_secret = "wechat_exe_secret_2024"
    
    headers, body_str = create_hmac_headers(app_id, app_secret, test_data)
    
    try:
        print("发送请求（仅包含avatar_style）...")
        response = requests.post(url, headers=headers, data=body_str, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ avatar_style字段测试通过")
                profile = result.get("profile", {})
                print(f"生成的画像摘要: {profile.get('summary', 'N/A')}")
                print(f"客户分类: {profile.get('category', 'N/A')}")
                return True
            else:
                print("❌ avatar_style字段测试失败 - API返回失败")
                return False
        else:
            print("❌ avatar_style字段测试失败 - HTTP状态码错误")
            return False
            
    except Exception as e:
        print(f"❌ avatar_style字段测试失败 - 异常: {str(e)}")
        return False

def test_both_fields():
    """测试同时包含nickname和avatar_style字段"""
    print("\n=== 测试4: 同时包含nickname和avatar_style字段 ===")
    
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
                "content": "今天天气不错，和朋友们一起爬山，心情很好！🏔️",
                "likes": ["friend3", "friend4", "friend5"],
                "comments": [
                    {"user": "friend3", "content": "风景真美！"},
                    {"user": "friend4", "content": "下次带我一起"}
                ],
                "user_actions": ["点赞", "分享"]
            },
            {
                "title": "美食分享",
                "content": "今天尝试了新的餐厅，味道不错！推荐给大家 👍",
                "likes": ["friend6", "friend7"],
                "comments": [
                    {"user": "friend6", "content": "看起来很好吃"},
                    {"user": "friend7", "content": "在哪里？"}
                ],
                "user_actions": ["点赞"]
            }
        ]
    }
    
    url = "http://127.0.0.1:5001/api/initial_sync"
    app_id = "wechat_exe_client"
    app_secret = "wechat_exe_secret_2024"
    
    headers, body_str = create_hmac_headers(app_id, app_secret, test_data)
    
    try:
        print("发送请求（包含所有新字段）...")
        response = requests.post(url, headers=headers, data=body_str, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 完整新字段功能测试通过")
                profile = result.get("profile", {})
                print(f"生成的画像摘要: {profile.get('summary', 'N/A')}")
                print(f"用户标签: {profile.get('labels', [])}")
                print(f"客户分类: {profile.get('category', 'N/A')}")
                print(f"兴趣爱好: {profile.get('hobbies', [])}")
                return True
            else:
                print("❌ 完整新字段功能测试失败 - API返回失败")
                return False
        else:
            print("❌ 完整新字段功能测试失败 - HTTP状态码错误")
            return False
            
    except Exception as e:
        print(f"❌ 完整新字段功能测试失败 - 异常: {str(e)}")
        return False

def test_empty_inputs():
    """测试空输入处理"""
    print("\n=== 测试5: 空输入处理 ===")
    
    test_data = {
        "user_id": "guangwolove",
        "user_wxid": "li258304281314", 
        "wechat_id": "pk_wgc",
        "nickname": "",
        "avatar_style": "",
        "moments": []
    }
    
    url = "http://127.0.0.1:5001/api/initial_sync"
    app_id = "wechat_exe_client"
    app_secret = "wechat_exe_secret_2024"
    
    headers, body_str = create_hmac_headers(app_id, app_secret, test_data)
    
    try:
        print("发送请求（所有输入为空）...")
        response = requests.post(url, headers=headers, data=body_str, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 400:
            result = response.json()
            if "所有输入参数均为空" in result.get("error", ""):
                print("✅ 空输入处理测试通过")
                return True
            else:
                print("❌ 空输入处理测试失败 - 错误信息不正确")
                return False
        else:
            print("❌ 空输入处理测试失败 - 应该返回400状态码")
            return False
            
    except Exception as e:
        print(f"❌ 空输入处理测试失败 - 异常: {str(e)}")
        return False

def main():
    print("开始测试朋友圈AI画像分析接口的nickname和avatar_style字段增强功能")
    print("=" * 80)
    
    test_results = []
    
    test_results.append(("向后兼容性", test_backward_compatibility()))
    test_results.append(("nickname字段", test_nickname_only()))
    test_results.append(("avatar_style字段", test_avatar_style_only()))
    test_results.append(("完整新字段功能", test_both_fields()))
    test_results.append(("空输入处理", test_empty_inputs()))
    
    print("\n" + "=" * 80)
    print("测试结果汇总:")
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有测试通过！nickname和avatar_style字段增强功能实现成功！")
        print("\n功能特点:")
        print("✅ 完全向后兼容，不影响现有功能")
        print("✅ 支持nickname字段，用于识别用户表达风格")
        print("✅ 支持avatar_style字段，用于推测视觉风格")
        print("✅ 智能处理空输入，避免无效分析")
        print("✅ AI画像分析结果包含完整的用户特征信息")
        return True
    else:
        print("⚠️  部分测试失败，请检查实现")
        return False

if __name__ == "__main__":
    main()
