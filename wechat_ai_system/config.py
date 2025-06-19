import os
import json
import logging
from typing import Dict, Any, Optional

CONFIG_FILE = "config_settings.json"

# 日志配置
import logging.handlers
os.makedirs('logs', exist_ok=True)  # 确保日志目录存在

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 数据库配置
DB_USER = "pkwgc"
DB_PASSWORD = "Wghfd@584521@fd"
DB_HOST = "rm-m5e0666vtv5234qi39o.mysql.rds.aliyuncs.com"
DB_PORT = "3306"
DB_NAME = "chatbot"

# 安全配置
IP_WHITELIST = []  # 允许访问的IP列表
IP_BLACKLIST = []  # 禁止访问的IP列表
RATE_LIMIT_PER_MINUTE = 600  # 每分钟API请求限制
USER_RATE_LIMIT_PER_MINUTE = 60  # 每个用户每分钟API请求限制
MAX_DAILY_REQUESTS_PER_USER = 1000  # 每个用户每天最大请求数
MAX_REQUEST_SIZE = 4096  # 用户消息最大字符数
ENABLE_USER_SPECIFIC_LIMITS = False  # 是否启用用户特定限制
MAX_CONNECTION_TIME = 30  # 单次连接最大时间（分钟）
CONNECTION_TIMEOUT = 60  # 连接超时时间（秒）

# 使用SQLite进行本地开发
USE_SQLITE = os.environ.get('USE_SQLITE', 'false').lower() == 'true'  # 检查环境变量
ENABLE_SOCKET_IO = True  # 启用SocketIO进行WebSocket通信
if USE_SQLITE:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///chatbot.db"
else:
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# API配置
DEEPSEEK_API_KEY = 'sk-swbvomdfkigmcgedqkcjzvwysijotkbvqjblgtspzxjrutnh'
DEEPSEEK_BASE_URL = 'https://api.siliconflow.cn/v1/'
MODEL = 'deepseek-ai/DeepSeek-V3'
MAX_TOKEN = 2000
TEMPERATURE = 1.1

# Moonshot API配置（用于图像识别）
MOONSHOT_API_KEY = 'sk-'
MOONSHOT_BASE_URL = 'https://api.moonshot.cn/v1'
MOONSHOT_MODEL = 'moonshot-v1-128k-vision-preview'
MOONSHOT_TEMPERATURE = 0.8
ENABLE_IMAGE_RECOGNITION = True
ENABLE_EMOJI_RECOGNITION = True

# 功能开关
ENABLE_AUTO_MESSAGE = True
AUTO_MESSAGE = '请你模拟系统设置的角色，在微信上找对方发消息想知道对方在做什么'
MIN_COUNTDOWN_HOURS = 1
MAX_COUNTDOWN_HOURS = 2
NOON_QUIET_TIME_START = '11:30'
NOON_QUIET_TIME_END = '13:30'
EVENING_QUIET_TIME_START = '22:00'
EVENING_QUIET_TIME_END = '07:00'

# 用户配置
TOKEN_LIMIT_DEFAULT = 0  # 0表示无限制
HAS_APPOINTMENT_DEFAULT = False

# 用户资料配置
ENABLE_USER_PROFILE = True  # 是否启用用户资料功能
USER_PROFILE_PLACEHOLDER_PREFIX = "{{"  # 用户资料占位符前缀
USER_PROFILE_PLACEHOLDER_SUFFIX = "}}"  # 用户资料占位符后缀

# 个性化提示词配置
ENABLE_PERSONALIZED_PROMPT = True  # 是否启用个性化提示词
PERSONALIZED_PROMPT_TEMPLATE = ""

CUSTOM_PLACEHOLDERS = """[]"""  # 存储JSON格式的自定义占位符列表



AI_RESPONSE_FORMAT = {
    "reply": "",  # AI回复内容
    "intent_type": "",  # specific_intent | no_intent | casual_chat
    "intent_details": {
        "name": None,  # 具体意图名称或null
        "confidence": 0.0,  # 置信度
        "entities": {}  # 提取的实体
    },
    "user_info_detected": {},  # 检测到的用户信息
    "order_info": None  # 订单信息（如果有）
}

AI_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["reply", "intent_type", "intent_details"],
    "properties": {
        "reply": {"type": "string"},
        "intent_type": {"type": "string", "enum": ["specific_intent", "no_intent", "casual_chat"]},
        "intent_details": {
            "type": "object",
            "required": ["name", "confidence", "entities"],
            "properties": {
                "name": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "entities": {"type": "object"}
            }
        },
        "user_info_detected": {"type": "object"},
        "order_info": {
            "type": ["object", "null"],
            "properties": {
                "order_id": {"type": "string"},
                "status": {"type": "string"},
                "products": {"type": "array"},
                "total_amount": {"type": "number"},
                "shipping_info": {"type": "object"}
            }
        }
    }
}

# 聊天配置
CHAT_ACTIVE_MINUTES = 30  # 判断用户是否在聊天状态的时间窗口（分钟）
GREETING_CONTEXT_MESSAGES = 5  # 问候功能检查的上下文消息数量
MAX_CONTEXT_LENGTH = 50  # 最大上下文长度
MAX_CONTEXT_MESSAGES = 10  # AI请求时使用的最大上下文消息数量

# 聊天记录存储配置
CHAT_STORAGE_DIR = "chat_records"  # 聊天记录JSON文件存储目录
ENABLE_JSON_STORAGE = True  # 是否启用JSON存储聊天记录
SYNC_DB_WITH_JSON = True  # 是否同步数据库和JSON文件的聊天记录

ENABLE_SOCKET_IO = True

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

MAX_CONTACTS_PER_USER = 5000  # 每个用户最多可以同步的联系人数量

DEFAULT_MAX_WECHAT_ACCOUNTS = 1  # 默认每个用户最多绑定的微信账号数
GLOBAL_MAX_WECHAT_ACCOUNTS = 10  # 全局最大微信账号绑定数限制

INTENT_LEVELS = {
    "高意向": {"score_min": 0.8, "keywords": ["购买", "下单", "要", "买"]},
    "一般意向": {"score_min": 0.5, "keywords": ["了解", "咨询", "看看"]},
    "沉默": {"score_min": 0.2, "keywords": []},
    "已成交": {"score_min": 1.0, "keywords": ["已付款", "收到货"]}
}

PROACTIVE_FOLLOW_CONFIG = {
    "成交客户": {"frequency": "weekly", "template": "复购关怀"},
    "高意向客户": {"frequency": "daily", "template": "意向跟进"},
    "潜在客户": {"frequency": "weekly", "template": "产品推荐"}
}

# 管理员配置
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

ENABLE_AUTO_REGISTRATION = False  # 禁用聊天接口自动注册

# 计费配置
TOKEN_COST_RATE = 0.01
TIME_COST_RATE = 0.1

# 配置字典
CONFIG = {
    "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
    "DEEPSEEK_BASE_URL": DEEPSEEK_BASE_URL,
    "MODEL": MODEL,
    "MAX_TOKEN": MAX_TOKEN,
    "TEMPERATURE": TEMPERATURE,
    "MOONSHOT_API_KEY": MOONSHOT_API_KEY,
    "MOONSHOT_BASE_URL": MOONSHOT_BASE_URL,
    "MOONSHOT_MODEL": MOONSHOT_MODEL,
    "MOONSHOT_TEMPERATURE": MOONSHOT_TEMPERATURE,
    "ENABLE_IMAGE_RECOGNITION": ENABLE_IMAGE_RECOGNITION,
    "ENABLE_EMOJI_RECOGNITION": ENABLE_EMOJI_RECOGNITION,
    "ENABLE_AUTO_MESSAGE": ENABLE_AUTO_MESSAGE,
    "TOKEN_LIMIT_DEFAULT": TOKEN_LIMIT_DEFAULT,
    "HAS_APPOINTMENT_DEFAULT": HAS_APPOINTMENT_DEFAULT,
    "ENABLE_USER_PROFILE": ENABLE_USER_PROFILE,
    "USER_PROFILE_PLACEHOLDER_PREFIX": USER_PROFILE_PLACEHOLDER_PREFIX,
    "USER_PROFILE_PLACEHOLDER_SUFFIX": USER_PROFILE_PLACEHOLDER_SUFFIX,
    "ENABLE_PERSONALIZED_PROMPT": ENABLE_PERSONALIZED_PROMPT,
    "PERSONALIZED_PROMPT_TEMPLATE": PERSONALIZED_PROMPT_TEMPLATE,
    "CUSTOM_PLACEHOLDERS": CUSTOM_PLACEHOLDERS,
    "CHAT_ACTIVE_MINUTES": CHAT_ACTIVE_MINUTES,
    "GREETING_CONTEXT_MESSAGES": GREETING_CONTEXT_MESSAGES,
    "MAX_CONTEXT_LENGTH": MAX_CONTEXT_LENGTH,
    "MAX_CONTEXT_MESSAGES": MAX_CONTEXT_MESSAGES,
    "AUTO_MESSAGE": AUTO_MESSAGE,
    "MIN_COUNTDOWN_HOURS": MIN_COUNTDOWN_HOURS,
    "MAX_COUNTDOWN_HOURS": MAX_COUNTDOWN_HOURS,
    "NOON_QUIET_TIME_START": NOON_QUIET_TIME_START,
    "NOON_QUIET_TIME_END": NOON_QUIET_TIME_END,
    "EVENING_QUIET_TIME_START": EVENING_QUIET_TIME_START,
    "EVENING_QUIET_TIME_END": EVENING_QUIET_TIME_END,
    "IP_WHITELIST": IP_WHITELIST,
    "IP_BLACKLIST": IP_BLACKLIST,
    "RATE_LIMIT_PER_MINUTE": RATE_LIMIT_PER_MINUTE,
    "USER_RATE_LIMIT_PER_MINUTE": USER_RATE_LIMIT_PER_MINUTE,
    "MAX_DAILY_REQUESTS_PER_USER": MAX_DAILY_REQUESTS_PER_USER,
    "MAX_REQUEST_SIZE": MAX_REQUEST_SIZE,
    "ENABLE_USER_SPECIFIC_LIMITS": ENABLE_USER_SPECIFIC_LIMITS,
    "MAX_CONNECTION_TIME": MAX_CONNECTION_TIME,
    "CONNECTION_TIMEOUT": CONNECTION_TIMEOUT,
    "AI_RESPONSE_FORMAT": AI_RESPONSE_FORMAT,
    "AI_RESPONSE_SCHEMA": AI_RESPONSE_SCHEMA,
    "HMAC_SECRET_KEYS": {
        "default_app": "your_secret_key_here",
        "wechat_exe_client": "wechat_exe_secret_2024"
    },
    "HMAC_REQUEST_TIMEOUT": 300
}

def save_config_to_file():
    """将配置保存到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, ensure_ascii=False, indent=4)
        logger.info(f"配置已保存到文件: {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"保存配置到文件失败: {str(e)}")
        return False

def load_config_from_file():
    """从文件加载配置"""
    global CONFIG
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                
                for key, value in saved_config.items():
                    if key in CONFIG:
                        CONFIG[key] = value
                        globals()[key] = value
                        
            logger.info(f"从文件加载配置成功: {CONFIG_FILE}")
            return True
        else:
            logger.warning(f"配置文件不存在，使用默认配置: {CONFIG_FILE}")
            return False
    except Exception as e:
        logger.error(f"从文件加载配置失败: {str(e)}")
        return False

def update_config(key: str, value: Any) -> bool:
    """更新配置"""
    global CONFIG
    
    if key in CONFIG:
        old_value = CONFIG[key]
        CONFIG[key] = value
        
        # 更新对应的全局变量
        globals()[key] = value
        
        save_config_to_file()
        
        logger.info(f"配置已更新: {key} = {value} (原值: {old_value})")
        return True
    else:
        logger.warning(f"尝试更新不存在的配置项: {key}")
        return False
def fill_placeholders(template: str, params: dict) -> str:
    """
    自动将模板字符串中的 {变量} 或 {{变量}} 替换为 params 里的内容。
    
    Args:
        template: 包含占位符的模板字符串
        params: 参数字典，键为占位符名称，值为替换内容
    
    Returns:
        替换后的字符串
    """
    import re
    
    def replacer(match):
        key = match.group(1) or match.group(2)
        if key in params and params[key] is not None:
            return str(params[key])
        else:
            return match.group(0)
    
    pattern = re.compile(r"\{\{(\w+)\}\}|\{(\w+)\}")
    result = pattern.sub(replacer, template)
    
    replaced_count = len([k for k in params.keys() if k in template and params[k] is not None])
    logger.info(f"占位符替换完成，替换了 {replaced_count} 个占位符")
    return result
