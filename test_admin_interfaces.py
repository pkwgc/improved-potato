import requests
import json
from datetime import datetime

def test_admin_login():
    """测试管理员登录"""
    session = requests.Session()
    
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = session.post(
            "http://localhost:5000/admin/login",
            data=login_data,
            timeout=10
        )
        
        if response.status_code == 200 or response.status_code == 302:
            print("✅ 管理员登录成功")
            return session
        else:
            print(f"❌ 管理员登录失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 管理员登录测试失败: {str(e)}")
        return None

def test_customer_profiling_page(session):
    """测试客户画像管理页面"""
    if not session:
        print("❌ 无法测试客户画像页面：未登录")
        return
    
    try:
        response = session.get(
            "http://localhost:5000/admin/customer-profiling",
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ 客户画像管理页面访问成功")
            if "客户画像管理" in response.text:
                print("✅ 页面内容正确")
            else:
                print("⚠️ 页面内容可能有问题")
        else:
            print(f"❌ 客户画像管理页面访问失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 客户画像页面测试失败: {str(e)}")

def test_ai_profiling_settings_page(session):
    """测试AI画像设置页面"""
    if not session:
        print("❌ 无法测试AI画像设置页面：未登录")
        return
    
    try:
        response = session.get(
            "http://localhost:5000/admin/ai_profiling",
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ AI画像设置页面访问成功")
            if "朋友圈AI画像分析设置" in response.text:
                print("✅ 页面内容正确")
            else:
                print("⚠️ 页面内容可能有问题")
        else:
            print(f"❌ AI画像设置页面访问失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ AI画像设置页面测试失败: {str(e)}")

def test_contacts_page(session):
    """测试联系人管理页面"""
    if not session:
        print("❌ 无法测试联系人管理页面：未登录")
        return
    
    try:
        response = session.get(
            "http://localhost:5000/admin/contacts",
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ 联系人管理页面访问成功")
            if "联系人管理" in response.text or "微信联系人" in response.text:
                print("✅ 页面内容正确")
            else:
                print("⚠️ 页面内容可能有问题")
        else:
            print(f"❌ 联系人管理页面访问失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 联系人管理页面测试失败: {str(e)}")

if __name__ == "__main__":
    print("开始测试管理员界面...")
    print("=" * 50)
    
    print("1. 测试管理员登录")
    session = test_admin_login()
    
    print("\n2. 测试客户画像管理页面")
    test_customer_profiling_page(session)
    
    print("\n3. 测试AI画像设置页面")
    test_ai_profiling_settings_page(session)
    
    print("\n4. 测试联系人管理页面")
    test_contacts_page(session)
    
    print("\n管理员界面测试完成！")
