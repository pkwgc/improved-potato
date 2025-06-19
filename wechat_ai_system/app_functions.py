"""
WebSocket应用功能模块
包含消息队列管理和WebSocket辅助函数
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def add_message_to_queue(user_id, message, user_message_queues):
    """添加消息到用户队列"""
    if user_id not in user_message_queues:
        user_message_queues[user_id] = {}
        
    message_id = message.get('id')
    if message_id:
        user_message_queues[user_id][message_id] = {
            'message': message,
            'timestamp': datetime.now(),
            'retry_count': 0
        }
        logger.debug(f"消息 {message_id} 已添加到用户 {user_id} 的队列")
        return True
    return False

def setup_app_functions(app, user_message_queues, user_wechat_rooms):
    """设置应用函数"""
    app.add_message_to_queue = lambda user_id, message: add_message_to_queue(user_id, message, user_message_queues)
    app.user_wechat_rooms = user_wechat_rooms
