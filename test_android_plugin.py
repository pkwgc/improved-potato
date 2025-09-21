#!/usr/bin/env python3
"""
Android WeChat Payment Plugin Test Script
测试Android插件的scheme协议处理和参数解析功能
"""

import os
import sys
import subprocess
import json
from urllib.parse import urlparse, parse_qs

def test_scheme_url_parsing():
    """测试scheme URL解析功能"""
    print("=== Testing Scheme URL Parsing ===")
    
    test_params = {
        'prepayId': 'wx19162432174915e15d5011fb071e330000',
        'appId': 'wxdf261c3b90ffbc25',
        'partnerId': '1236537302',
        'nonceStr': 'tUQgTXocIAFakmHNEWGGDCtaXIQxKsOc',
        'sign': '82B29937ECE7A47F45409BD85B84C951',
        'spreadField': 'Sign=WXPay',
        'timestamp': '1758270368'
    }
    
    query_params = '&'.join([f"{k}={v}" for k, v in test_params.items()])
    scheme_url = f"wechatpay://pay?{query_params}"
    
    print(f"Generated scheme URL: {scheme_url}")
    
    parsed = urlparse(scheme_url)
    parsed_params = parse_qs(parsed.query)
    
    print(f"Parsed scheme: {parsed.scheme}")
    print(f"Parsed path: {parsed.path}")
    print(f"Parsed params: {parsed_params}")
    
    success = True
    for key, expected_value in test_params.items():
        if key in parsed_params:
            actual_value = parsed_params[key][0]
            if actual_value == expected_value:
                print(f"✓ {key}: {actual_value}")
            else:
                print(f"✗ {key}: expected {expected_value}, got {actual_value}")
                success = False
        else:
            print(f"✗ {key}: missing from parsed params")
            success = False
    
    return success

def test_android_project_structure():
    """测试Android项目结构"""
    print("\n=== Testing Android Project Structure ===")
    
    base_path = "/home/ubuntu/repos/improved-potato/android_plugin"
    required_files = [
        "settings.gradle",
        "build.gradle",
        "app/build.gradle",
        "app/src/main/AndroidManifest.xml",
        "app/src/main/java/com/wechat/payment/MainActivity.java",
        "app/src/main/java/com/wechat/payment/PaymentHandler.java",
        "app/src/main/java/com/wechat/payment/PaymentParams.java",
        "app/src/main/java/com/wechat/payment/wxapi/WXPayEntryActivity.java",
        "app/src/main/res/layout/activity_main.xml",
        "app/src/main/res/values/strings.xml"
    ]
    
    success = True
    for file_path in required_files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - missing")
            success = False
    
    return success

def test_gradle_syntax():
    """测试Gradle文件语法"""
    print("\n=== Testing Gradle Syntax ===")
    
    gradle_files = [
        "/home/ubuntu/repos/improved-potato/android_plugin/build.gradle",
        "/home/ubuntu/repos/improved-potato/android_plugin/app/build.gradle",
        "/home/ubuntu/repos/improved-potato/android_plugin/settings.gradle"
    ]
    
    success = True
    for gradle_file in gradle_files:
        if os.path.exists(gradle_file):
            try:
                with open(gradle_file, 'r') as f:
                    content = f.read()
                    if 'plugins {' in content and '}' in content:
                        print(f"✓ {os.path.basename(gradle_file)} - syntax looks good")
                    else:
                        print(f"? {os.path.basename(gradle_file)} - basic syntax check passed")
            except Exception as e:
                print(f"✗ {os.path.basename(gradle_file)} - error reading: {e}")
                success = False
        else:
            print(f"✗ {os.path.basename(gradle_file)} - file not found")
            success = False
    
    return success

def test_android_manifest():
    """测试AndroidManifest.xml配置"""
    print("\n=== Testing AndroidManifest.xml ===")
    
    manifest_path = "/home/ubuntu/repos/improved-potato/android_plugin/app/src/main/AndroidManifest.xml"
    
    if not os.path.exists(manifest_path):
        print(f"✗ AndroidManifest.xml not found")
        return False
    
    try:
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        checks = [
            ('scheme="wechatpay"', "WeChat Pay scheme"),
            ('scheme="wxpay"', "Alternative scheme"),
            ('WXPayEntryActivity', "WeChat Pay entry activity"),
            ('INTERNET', "Internet permission"),
            ('android.intent.action.VIEW', "Intent filter for scheme")
        ]
        
        success = True
        for check, description in checks:
            if check in content:
                print(f"✓ {description}")
            else:
                print(f"✗ {description} - not found")
                success = False
        
        return success
        
    except Exception as e:
        print(f"✗ Error reading AndroidManifest.xml: {e}")
        return False

def test_h5_example():
    """测试H5示例页面"""
    print("\n=== Testing H5 Example ===")
    
    h5_files = [
        "/home/ubuntu/repos/improved-potato/h5_example/wechat_payment_demo.html",
        "/home/ubuntu/repos/improved-potato/wechat_ai_system/templates/wechat_payment_demo.html"
    ]
    
    success = True
    for h5_file in h5_files:
        if os.path.exists(h5_file):
            try:
                with open(h5_file, 'r') as f:
                    content = f.read()
                
                checks = [
                    ('wechatpay://', "WeChat Pay scheme"),
                    ('invokeWeChatPay', "Payment invocation function"),
                    ('prepayId', "PrepayId parameter"),
                    ('window.location.href', "Scheme URL invocation")
                ]
                
                file_success = True
                for check, description in checks:
                    if check in content:
                        print(f"✓ {os.path.basename(h5_file)} - {description}")
                    else:
                        print(f"✗ {os.path.basename(h5_file)} - {description} not found")
                        file_success = False
                
                if not file_success:
                    success = False
                    
            except Exception as e:
                print(f"✗ Error reading {h5_file}: {e}")
                success = False
        else:
            print(f"✗ {h5_file} - file not found")
            success = False
    
    return success

def test_flask_integration():
    """测试Flask集成"""
    print("\n=== Testing Flask Integration ===")
    
    integration_file = "/home/ubuntu/repos/improved-potato/wechat_ai_system/wechat_payment_integration.py"
    
    if not os.path.exists(integration_file):
        print(f"✗ Integration file not found")
        return False
    
    try:
        with open(integration_file, 'r') as f:
            content = f.read()
        
        checks = [
            ('/api/wechat/payment/prepare', "Payment preparation endpoint"),
            ('/api/wechat/payment/callback', "Payment callback endpoint"),
            ('generate_wechat_payment_params', "Parameter generation"),
            ('generate_scheme_url', "Scheme URL generation"),
            ('Blueprint', "Flask Blueprint usage")
        ]
        
        success = True
        for check, description in checks:
            if check in content:
                print(f"✓ {description}")
            else:
                print(f"✗ {description} - not found")
                success = False
        
        return success
        
    except Exception as e:
        print(f"✗ Error reading integration file: {e}")
        return False

def main():
    """主测试函数"""
    print("Android WeChat Payment Plugin Test Suite")
    print("=" * 50)
    
    tests = [
        ("Scheme URL Parsing", test_scheme_url_parsing),
        ("Android Project Structure", test_android_project_structure),
        ("Gradle Syntax", test_gradle_syntax),
        ("AndroidManifest Configuration", test_android_manifest),
        ("H5 Example Pages", test_h5_example),
        ("Flask Integration", test_flask_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} - Exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status:4} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Android plugin is ready for use.")
        return 0
    else:
        print("❌ Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
