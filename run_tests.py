#!/usr/bin/env python3
import subprocess
import sys
import time
import os

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.stdout:
            print("标准输出:")
            print(result.stdout)
        
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - 成功")
        else:
            print(f"❌ {description} - 失败 (返回码: {result.returncode})")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - 超时")
        return False
    except Exception as e:
        print(f"❌ {description} - 异常: {str(e)}")
        return False

def check_dependencies():
    """检查依赖是否安装"""
    print("检查Python依赖...")
    
    dependencies = [
        "flask", "flask_socketio", "eventlet", "pymysql", 
        "requests", "sqlalchemy", "flask_sqlalchemy", 
        "python_dotenv", "cryptography", "pillow", "jsonschema"
    ]
    
    missing_deps = []
    
    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} - 缺失")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n缺失依赖: {', '.join(missing_deps)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖已安装")
    return True

def test_syntax():
    """测试Python语法"""
    print("\n检查Python文件语法...")
    
    python_files = [
        "app.py",
        "ai_api_client.py", 
        "database.py",
        "config.py",
        "test_ai_profiling_workflow.py",
        "test_admin_interfaces.py"
    ]
    
    all_good = True
    
    for file in python_files:
        if os.path.exists(file):
            result = run_command(f"python -m py_compile {file}", f"语法检查 {file}")
            if not result:
                all_good = False
        else:
            print(f"⚠️ 文件不存在: {file}")
    
    return all_good

def main():
    """主测试函数"""
    print("微信朋友圈AI画像系统 - 综合测试")
    print("=" * 60)
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    success_count = 0
    total_tests = 3
    
    if check_dependencies():
        success_count += 1
    
    if test_syntax():
        success_count += 1
    
    print(f"\n{'='*60}")
    print("测试摘要")
    print(f"{'='*60}")
    print(f"通过测试: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 所有测试通过！系统准备就绪")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查上述错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())
