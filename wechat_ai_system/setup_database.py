#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
try:
    from config import DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME
except ImportError:
    DATABASE_HOST = 'localhost'
    DATABASE_PORT = 3306
    DATABASE_USER = 'root'
    DATABASE_PASSWORD = 'password'
    DATABASE_NAME = 'wechat_ai_system'
import pymysql

def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    try:
        connection = pymysql.connect(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DATABASE_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ 数据库 '{DATABASE_NAME}' 已创建或已存在")
        
        connection.commit()
        connection.close()
        
    except Exception as e:
        print(f"❌ 创建数据库失败: {str(e)}")
        return False
    
    return True

def setup_tables():
    """初始化数据库表"""
    try:
        from database import Base, engine
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表初始化成功")
        return True
    except Exception as e:
        print(f"❌ 初始化数据库表失败: {str(e)}")
        return False

def create_admin_user():
    """创建管理员用户"""
    try:
        from database import User
        
        db = next(get_db())
        
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                password='admin123',
                user_id='admin_001',
                is_admin=True,
                token_balance=10000
            )
            db.add(admin_user)
            db.commit()
            print("✅ 管理员用户创建成功 (用户名: admin, 密码: admin123)")
        else:
            print("✅ 管理员用户已存在")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {str(e)}")
        return False

def create_ai_strategy():
    """创建默认AI策略"""
    try:
        from database import AIStrategy
        try:
            from config import AI_PROFILING_PROMPT_TEMPLATE, AI_PROFILING_SYSTEM_MESSAGE, AI_PROFILING_TEMPERATURE, AI_PROFILING_MAX_TOKENS
        except ImportError:
            AI_PROFILING_PROMPT_TEMPLATE = """
请分析以下朋友圈内容，生成用户画像：

朋友圈内容：
{moments_content}

请以JSON格式返回分析结果，包含以下字段：
- summary: 用户总体描述
- labels: 用户标签列表
- category: 用户分类（如：高价值客户、普通客户、潜在客户等）
- hobbies: 兴趣爱好列表
"""
            AI_PROFILING_SYSTEM_MESSAGE = "你是一个专业的用户画像分析师，擅长从社交媒体内容中分析用户特征和偏好。"
            AI_PROFILING_TEMPERATURE = 0.3
            AI_PROFILING_MAX_TOKENS = 2000
        
        db = next(get_db())
        
        ai_strategy = db.query(AIStrategy).filter(AIStrategy.name == 'moments_profiling').first()
        if not ai_strategy:
            ai_strategy = AIStrategy(
                name='moments_profiling',
                description='朋友圈AI画像分析策略',
                prompt_template=AI_PROFILING_PROMPT_TEMPLATE,
                system_message=AI_PROFILING_SYSTEM_MESSAGE,
                temperature=AI_PROFILING_TEMPERATURE,
                max_tokens=AI_PROFILING_MAX_TOKENS
            )
            db.add(ai_strategy)
            db.commit()
            print("✅ 默认AI策略创建成功")
        else:
            print("✅ AI策略已存在")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 创建AI策略失败: {str(e)}")
        return False

def main():
    """主安装函数"""
    print("微信朋友圈AI画像系统 - 数据库安装")
    print("=" * 50)
    
    success_count = 0
    total_steps = 4
    
    print("1. 创建数据库...")
    if create_database_if_not_exists():
        success_count += 1
    
    print("\n2. 初始化数据库表...")
    if setup_tables():
        success_count += 1
    
    print("\n3. 创建管理员用户...")
    if create_admin_user():
        success_count += 1
    
    print("\n4. 创建默认AI策略...")
    if create_ai_strategy():
        success_count += 1
    
    print(f"\n{'='*50}")
    print("安装摘要")
    print(f"{'='*50}")
    print(f"完成步骤: {success_count}/{total_steps}")
    
    if success_count == total_steps:
        print("🎉 数据库安装完成！")
        print("\n下一步:")
        print("1. 配置 .env 文件中的 DEEPSEEK_API_KEY")
        print("2. 运行: python app.py")
        print("3. 访问: http://localhost:5000/admin (用户名: admin, 密码: admin123)")
        return 0
    else:
        print("⚠️ 部分安装步骤失败，请检查上述错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())
