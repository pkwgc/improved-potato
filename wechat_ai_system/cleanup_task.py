"""
清理过期连接和消息队列的任务
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def cleanup_expired_connections(app, socketio, user_socket_map, user_last_heartbeat, user_message_queues):
    """清理过期的连接和消息队列"""
    try:
        now = datetime.now()
        expired_users = []
        
        for user_id, last_heartbeat in user_last_heartbeat.items():
            if (now - last_heartbeat).total_seconds() > 60:  # 60秒无心跳视为断开
                expired_users.append(user_id)
                logger.info(f"用户 {user_id} 心跳超时，清理连接")
                
        for user_id in expired_users:
            if user_id in user_socket_map:
                socketio.emit('disconnect', to=user_socket_map[user_id])
                user_socket_map.pop(user_id)
                
            if user_id in user_last_heartbeat:
                user_last_heartbeat.pop(user_id)
                
            if user_id in user_message_queues:
                user_message_queues.pop(user_id)
                
            if hasattr(app, 'user_wechat_rooms') and user_id in app.user_wechat_rooms:
                app.user_wechat_rooms.pop(user_id)
                
        for user_id, messages in list(user_message_queues.items()):
            if user_id not in user_socket_map:
                continue
                
            for message_id, message_data in list(messages.items()):
                message = message_data['message']
                timestamp = message_data['timestamp']
                retry_count = message_data['retry_count']
                
                if (now - timestamp).total_seconds() > 30 and retry_count < 3:
                    socketio.emit('new_message', message, to=user_socket_map[user_id])
                    messages[message_id]['retry_count'] += 1
                    messages[message_id]['timestamp'] = now
                    logger.info(f"重发消息 {message_id} 给用户 {user_id}，重试次数: {retry_count + 1}")
                    
                elif retry_count >= 3:
                    messages.pop(message_id)
                    logger.warning(f"消息 {message_id} 重试次数达到上限，从队列中移除")
    except Exception as e:
        logger.error(f"清理过期连接失败: {str(e)}")
