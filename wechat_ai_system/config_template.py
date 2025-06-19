import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'your_deepseek_api_key_here')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
MODEL = os.getenv('MODEL', 'deepseek-chat')
MAX_TOKEN = int(os.getenv('MAX_TOKEN', '4000'))
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))

DATABASE_HOST = os.getenv('DATABASE_HOST', 'localhost')
DATABASE_PORT = int(os.getenv('DATABASE_PORT', '3306'))
DATABASE_USER = os.getenv('DATABASE_USER', 'root')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', 'password')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'wechat_ai_system')

AI_PROFILING_PROMPT_TEMPLATE = """
请分析以下朋友圈内容，生成用户画像：

朋友圈内容：
{moments_content}

请以JSON格式返回分析结果，包含以下字段：
- summary: 用户总体描述
- labels: 用户标签列表
- category: 用户分类（如：高价值客户、普通客户、潜在客户等）
- hobbies: 兴趣爱好列表

示例格式：
{
    "summary": "喜欢美食和旅行的活跃用户",
    "labels": ["美食爱好者", "旅行达人", "社交活跃"],
    "category": "高价值客户",
    "hobbies": ["美食", "旅行", "摄影"]
}
"""

AI_PROFILING_SYSTEM_MESSAGE = "你是一个专业的用户画像分析师，擅长从社交媒体内容中分析用户特征和偏好。"
AI_PROFILING_TEMPERATURE = 0.3
AI_PROFILING_MAX_TOKENS = 2000

ENABLE_AI_PROFILING = True
ENABLE_USER_PROFILE = True
ENABLE_RATE_LIMITING = True

SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key_here')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
