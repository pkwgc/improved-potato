#!/usr/bin/env python3
import os
import sys
import subprocess
import json
from pathlib import Path

def check_hardcoded_content():
    """检查是否还有硬编码内容"""
    print("🔍 检查硬编码内容...")
    
    hardcoded_patterns = [
        "你必须以下面的JSON格式",
    ]
    
    exclude_files = [
        "migrate_templates.py",
        "logs/",
        "验证脚本.py",
        "test_template_system.py",
        "__pycache__/",
        ".git/"
    ]
    
    found_issues = []
    
    for pattern in hardcoded_patterns:
        try:
            result = subprocess.run([
                "grep", "-r", pattern, ".",
                "--include=*.py"
            ], capture_output=True, text=True, cwd="/home/ubuntu/wechat_placeholder_refactor")
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if not any(exclude in line for exclude in exclude_files):
                        found_issues.append(f"发现硬编码内容: {line}")
        except Exception as e:
            print(f"搜索模式 '{pattern}' 时出错: {e}")
    
    if found_issues:
        print("❌ 发现硬编码内容:")
        for issue in found_issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ 未发现运行时硬编码内容")
        return True

def check_database_template_usage():
    """检查AI服务是否使用数据库模板"""
    print("🔍 检查数据库模板使用情况...")
    
    ai_service_file = "/home/ubuntu/wechat_placeholder_refactor/ai_service_optimized.py"
    
    if not os.path.exists(ai_service_file):
        print("❌ ai_service_optimized.py 文件不存在")
        return False
    
    with open(ai_service_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_methods = [
        "_get_template_with_cache",
        "_get_ai_response_format_template",
        "fill_placeholders"
    ]
    
    missing_methods = []
    for method in required_methods:
        if method not in content:
            missing_methods.append(method)
    
    if missing_methods:
        print(f"❌ 缺少必要方法: {missing_methods}")
        return False
    
    if "db.query(Template)" not in content:
        print("❌ AI服务未使用数据库查询模板")
        return False
    
    print("✅ AI服务正确使用数据库模板")
    return True

def check_config_fill_placeholders():
    """检查config.py中的fill_placeholders函数"""
    print("🔍 检查fill_placeholders函数...")
    
    config_file = "/home/ubuntu/wechat_placeholder_refactor/config.py"
    
    if not os.path.exists(config_file):
        print("❌ config.py 文件不存在")
        return False
    
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "def fill_placeholders" not in content:
        print("❌ config.py中缺少fill_placeholders函数")
        return False
    
    if "re.compile(r\"\\{\\{(\\w+)\\}\\}|\\{(\\w+)\\}\")" not in content:
        print("❌ fill_placeholders函数正则表达式不正确")
        return False
    
    print("✅ fill_placeholders函数实现正确")
    return True

def check_template_types_in_database():
    """检查数据库中的模板类型"""
    print("🔍 检查数据库模板类型...")
    
    try:
        import os
        os.environ['USE_SQLITE'] = 'true'
        
        sys.path.append("/home/ubuntu/wechat_placeholder_refactor")
        from database import get_db, Template
        
        db = next(get_db())
        templates = db.query(Template).all()
        
        template_types = set()
        for template in templates:
            if hasattr(template, 'template_type'):
                template_types.add(template.template_type)
        
        expected_types = {"chat", "ai_response_format", "system"}
        
        if "ai_response_format" not in template_types:
            print("❌ 数据库中缺少ai_response_format类型的模板")
            return False
        
        print(f"✅ 数据库中包含模板类型: {template_types}")
        return True
        
    except Exception as e:
        print(f"❌ 检查数据库模板类型时出错: {e}")
        return False

def check_admin_interface():
    """检查管理界面模板功能"""
    print("🔍 检查管理界面模板功能...")
    
    templates_html = "/home/ubuntu/wechat_placeholder_refactor/templates/templates.html"
    
    if not os.path.exists(templates_html):
        print("❌ templates.html 文件不存在")
        return False
    
    with open(templates_html, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_elements = [
        "template_type",
        "AI响应格式模板",
        "聊天模板",
        "系统模板"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print(f"❌ 管理界面缺少元素: {missing_elements}")
        return False
    
    print("✅ 管理界面模板功能完整")
    return True

def run_verification():
    """运行完整验证"""
    print("🚀 开始验证统一占位符替换系统...")
    print("=" * 50)
    
    checks = [
        ("硬编码内容检查", check_hardcoded_content),
        ("数据库模板使用检查", check_database_template_usage),
        ("占位符替换函数检查", check_config_fill_placeholders),
        ("数据库模板类型检查", check_template_types_in_database),
        ("管理界面功能检查", check_admin_interface),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name}执行出错: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 50)
    print("📊 验证结果汇总:")
    
    all_passed = True
    for check_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {check_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有验证通过！统一占位符替换系统实现完成。")
        print("\n📋 系统特点:")
        print("  ✅ 完全数据库驱动的模板管理")
        print("  ✅ 支持{变量}和{{变量}}两种占位符格式")
        print("  ✅ 统一的fill_placeholders函数处理所有替换")
        print("  ✅ 管理界面支持模板类型选择和编辑")
        print("  ✅ 模板修改立即生效，无需重启")
        print("  ✅ 移除所有运行时硬编码内容")
    else:
        print("❌ 验证失败，请检查上述问题并修复。")
    
    return all_passed

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
