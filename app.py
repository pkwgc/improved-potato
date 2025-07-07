"""
WeChat AI Chatbot System - Main Application Entry Point
"""
from flask import Flask, request
from flask_socketio import emit, join_room, leave_room
import os
import sys
import logging
import threading
from datetime import datetime

from extensions import init_extensions
from routes import register_blueprints
from database import create_tables

app = Flask(__name__)
app.secret_key = os.urandom(24)

socketio = init_extensions(app)

register_blueprints(app)

user_socket_map = {}
user_last_heartbeat = {}
user_message_queues = {}
user_wechat_rooms = {}
shutdown_event = threading.Event()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from proactive_messaging import ProactiveMessagingService
    from ai_api_client import CustomerProfilingService
    customer_profiling_service = CustomerProfilingService()
    proactive_messaging_service = ProactiveMessagingService(socketio)
except ImportError as e:
    logger.warning(f"Could not import services: {e}")

try:
    from api_messages import register_api_messages
    from api_send_message import register_api_send_message
    register_api_messages(app)
    register_api_send_message(app, socketio)
except ImportError as e:
    logger.warning(f"Could not register API modules: {e}")

try:
    from app_functions import setup_app_functions
    setup_app_functions(app, user_message_queues, user_wechat_rooms)
except ImportError:
    logger.warning("app_functions module not found, skipping setup")

@socketio.on('connect')
def handle_connect():
    logger.info(f"客户端连接: {request.sid}")
    
    welcome_message = {
        "type": "system",
        "content": "欢迎连接到WebSocket服务器！",
        "timestamp": datetime.now().isoformat()
    }
    socketio.emit('new_message', welcome_message, to=request.sid)
    
    if not hasattr(app, '_cleanup_lock'):
        app._cleanup_lock = threading.Lock()
    
    def cleanup_task():
        try:
            from cleanup_task import cleanup_expired_connections
            while True:
                socketio.sleep(60)
                try:
                    cleanup_expired_connections(app, socketio, user_socket_map, user_last_heartbeat, user_message_queues)
                except Exception as e:
                    logger.exception("清理任务执行异常")
        except ImportError:
            logger.warning("cleanup_task module not found")
    
    with app._cleanup_lock:
        if not getattr(app, 'cleanup_task_started', False):
            app.cleanup_task_started = True
            socketio.start_background_task(cleanup_task)

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    disconnected_user = None
    for user_id, socket_id in user_socket_map.items():
        if socket_id == request.sid:
            disconnected_user = user_id
            break
    
    if disconnected_user:
        logger.info(f"用户断开连接: {disconnected_user} (socket: {request.sid})")
        user_socket_map.pop(disconnected_user, None)
        user_last_heartbeat.pop(disconnected_user, None)
    else:
        logger.info(f"未知客户端断开连接: {request.sid}")

def initialize_database():
    try:
        create_tables()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")

if __name__ == '__main__':
    initialize_database()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
