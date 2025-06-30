import os
from dotenv import load_dotenv

load_dotenv()

ENABLE_SOCKET_IO = True

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
MODEL = os.getenv('MODEL', 'deepseek-chat')
MAX_TOKEN = int(os.getenv('MAX_TOKEN', '2000'))
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))

DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'wechat_system')

USE_SQLITE = os.environ.get('USE_SQLITE', 'true').lower() == 'true'

TOKEN_LIMIT_DEFAULT = int(os.getenv('TOKEN_LIMIT_DEFAULT', '10000'))
HAS_APPOINTMENT_DEFAULT = os.getenv('HAS_APPOINTMENT_DEFAULT', 'false').lower() == 'true'

ENABLE_USER_PROFILE = os.getenv('ENABLE_USER_PROFILE', 'true').lower() == 'true'
ENABLE_PERSONALIZED_PROMPT = os.getenv('ENABLE_PERSONALIZED_PROMPT', 'true').lower() == 'true'
PERSONALIZED_PROMPT_TEMPLATE = os.getenv('PERSONALIZED_PROMPT_TEMPLATE', '')

CUSTOM_PLACEHOLDERS = os.getenv('CUSTOM_PLACEHOLDERS', '[]')
CHAT_ACTIVE_MINUTES = int(os.getenv('CHAT_ACTIVE_MINUTES', '30'))
GREETING_CONTEXT_MESSAGES = int(os.getenv('GREETING_CONTEXT_MESSAGES', '5'))

MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', '8000'))
MAX_CONTEXT_MESSAGES = int(os.getenv('MAX_CONTEXT_MESSAGES', '20'))

AUTO_MESSAGE = os.getenv('AUTO_MESSAGE', '您好，有什么可以帮助您的吗？')
ENABLE_AUTO_MESSAGE = os.getenv('ENABLE_AUTO_MESSAGE', 'false').lower() == 'true'

MIN_COUNTDOWN_HOURS = int(os.getenv('MIN_COUNTDOWN_HOURS', '1'))
MAX_COUNTDOWN_HOURS = int(os.getenv('MAX_COUNTDOWN_HOURS', '24'))

NOON_QUIET_TIME_START = os.getenv('NOON_QUIET_TIME_START', '12:00')
NOON_QUIET_TIME_END = os.getenv('NOON_QUIET_TIME_END', '14:00')
EVENING_QUIET_TIME_START = os.getenv('EVENING_QUIET_TIME_START', '22:00')
EVENING_QUIET_TIME_END = os.getenv('EVENING_QUIET_TIME_END', '08:00')

AI_RESPONSE_FORMAT = os.getenv('AI_RESPONSE_FORMAT', 'json')

def load_config_from_file():
    pass

def fill_placeholders(template, data):
    result = template
    for key, value in data.items():
        placeholder = f"{{{key}}}"
        if placeholder in result:
            result = result.replace(placeholder, str(value))
    return result
