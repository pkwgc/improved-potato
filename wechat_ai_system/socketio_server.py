"""
直接Socket.IO服务器 - 修复版
不依赖Flask-SocketIO的事件系统，直接处理WebSocket连接和Socket.IO协议
专为易语言WebSocket客户端设计
"""
import eventlet
eventlet.monkey_patch()

import json
import logging
import time
import threading
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sessions = {}  # sid -> {user_id, ws, authenticated, rooms, last_heartbeat, message_queue}
user_sessions = {}  # user_id -> sid
rooms = {}  # room_name -> [sid]
pending_messages = {}  # message_id -> {sid, data, retry_count, timestamp}

def handle_websocket(ws):
    """处理WebSocket连接"""
    sid = f"sid_{int(time.time() * 1000)}"
    logger.info(f"新WebSocket连接: {sid}")
    
    sessions[sid] = {
        'user_id': None,
        'ws': ws,
        'authenticated': False,
        'rooms': [],
        'last_heartbeat': time.time(),
        'message_queue': []
    }
    
    handshake = {
        'sid': sid,
        'upgrades': [],
        'pingTimeout': 20000,
        'pingInterval': 25000,
        'maxPayload': 1000000
    }
    ws.send(f"0{json.dumps(handshake)}")
    logger.info(f"发送握手消息: {json.dumps(handshake, ensure_ascii=False)}")
    
    ws.send("40")
    logger.info("发送40连接确认消息")
    
    try:
        while True:
            message = ws.wait()
            if message is None:
                logger.info(f"连接关闭: {sid}")
                break
            
            logger.info(f"收到消息: {message}")
            
            if message == '2':
                logger.debug(f"收到心跳消息，发送心跳响应: {sid}")
                ws.send('3')
                continue
            
            if message.startswith('42'):
                try:
                    json_part = message[2:]
                    data = json.loads(json_part)
                    
                    if len(data) >= 2:
                        event_name = data[0]
                        event_data = data[1]
                        
                        logger.info(f"解析事件: {event_name}, 数据: {json.dumps(event_data, ensure_ascii=False)}")
                        
                        if event_name == 'authenticate':
                            handle_authenticate(sid, ws, event_data)
                            
                        elif event_name == 'join_wechat_room':
                            handle_join_room(sid, ws, event_data)
                            
                        elif event_name == 'send_direct_message':
                            handle_send_message(sid, ws, event_data)
                            
                        elif event_name == 'message_ack':
                            handle_message_ack(sid, ws, event_data)
                            
                        elif event_name == 'heartbeat':
                            handle_heartbeat(sid, ws, event_data)
                            
                        else:
                            logger.warning(f"未知事件: {event_name}")
                            
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {str(e)}, 原始消息: {message}")
                except Exception as e:
                    logger.error(f"处理事件消息出错: {str(e)}")
                    
    except Exception as e:
        logger.error(f"WebSocket处理错误: {str(e)}")
    finally:
        cleanup_session(sid)

def cleanup_session(sid):
    """清理会话"""
    if sid in sessions:
        for room in sessions[sid].get('rooms', []):
            if room in rooms and sid in rooms[room]:
                rooms[room].remove(sid)
                if not rooms[room]:
                    del rooms[room]
        
        user_id = sessions[sid].get('user_id')
        if user_id and user_id in user_sessions and user_sessions[user_id] == sid:
            del user_sessions[user_id]
        
        del sessions[sid]
        logger.info(f"清理会话: {sid}")

def handle_authenticate(sid, ws, data):
    """处理认证事件"""
    user_id = data.get('user_id')
    
    if not user_id:
        send_error(ws, 'missing_user_id', '缺少user_id参数')
        return
    
    sessions[sid]['user_id'] = user_id
    sessions[sid]['authenticated'] = True
    user_sessions[user_id] = sid
    
    auth_response = {'user_id': user_id, 'status': 'authenticated'}
    send_event(ws, 'auth_success', auth_response)
    logger.info(f"用户 {user_id} 认证成功")

def handle_join_room(sid, ws, data):
    """处理加入房间事件"""
    user_id = data.get('user_id')
    wechat_id = data.get('wechat_id')
    
    if not user_id or not wechat_id:
        send_error(ws, 'missing_params', '缺少必要参数')
        return
    
    if not is_authenticated(sid, user_id):
        send_error(ws, 'not_authenticated', '未认证或会话ID不匹配')
        return
    
    room = f'wechat_{wechat_id}'
    if room not in sessions[sid]['rooms']:
        sessions[sid]['rooms'].append(room)
    
    if room not in rooms:
        rooms[room] = []
    if sid not in rooms[room]:
        rooms[room].append(sid)
    
    room_response = {'wechat_id': wechat_id, 'room_id': room}
    send_event(ws, 'joined_wechat_room', room_response)
    logger.info(f"用户 {user_id} 加入房间 {room}")

def handle_send_message(sid, ws, data):
    """处理发送消息事件"""
    user_id = data.get('user_id')
    wechat_id = data.get('wechat_id')
    contact_id = data.get('contact_id')
    content = data.get('content')
    content_type = data.get('content_type', 'text')
    
    if not user_id or not wechat_id or not contact_id or not content:
        send_error(ws, 'missing_params', '缺少必要参数')
        return
    
    if not is_authenticated(sid, user_id):
        send_error(ws, 'not_authenticated', '未认证或会话ID不匹配')
        return
    
    message_id = f'msg_{int(time.time()*1000)}'
    
    send_event(ws, 'message_sent', {'status': 'sent', 'message_id': message_id})
    
    room = f'wechat_{wechat_id}'
    new_message = {
        'id': message_id,
        'type': 'message',
        'content': content,
        'content_type': content_type,
        'sender': {'id': user_id, 'name': user_id},
        'receiver': {'id': contact_id, 'name': contact_id, 'is_group': False},
        'timestamp': datetime.now().isoformat(),
        'require_ack': True
    }
    
    broadcast_to_room(room, 'new_message', new_message)
    logger.info(f"推送WebSocket消息到房间: {room}, 内容: {json.dumps(new_message, ensure_ascii=False)}")
    
    def send_reply():
        time.sleep(1)
        reply_id = f'reply_{int(time.time()*1000)}'
        reply_message = {
            'id': reply_id,
            'type': 'message',
            'content': f'收到你的消息: {content}',
            'content_type': 'text',
            'sender': {'id': contact_id, 'name': contact_id},
            'receiver': {'id': user_id, 'name': user_id, 'is_group': False},
            'timestamp': datetime.now().isoformat(),
            'require_ack': True
        }
        
        broadcast_to_room(room, 'new_message', reply_message)
        logger.info(f"推送回复消息到房间: {room}, 内容: {json.dumps(reply_message, ensure_ascii=False)}")
    
    threading.Thread(target=send_reply).start()

def handle_message_ack(sid, ws, data):
    """处理消息确认事件"""
    user_id = data.get('user_id')
    message_id = data.get('message_id')
    
    if not user_id or not message_id:
        send_error(ws, 'missing_params', '缺少必要参数')
        return
    
    if not is_authenticated(sid, user_id):
        send_error(ws, 'not_authenticated', '未认证或会话ID不匹配')
        return
    
    send_event(ws, 'ack_received', {'message_id': message_id, 'status': 'acknowledged'})
    logger.info(f"消息 {message_id} 确认成功")

def handle_heartbeat(sid, ws, data):
    """处理心跳事件"""
    user_id = data.get('user_id')
    if sid in sessions:
        sessions[sid]['last_heartbeat'] = time.time()
        
        if sessions[sid]['message_queue']:
            for queued_message in sessions[sid]['message_queue']:
                try:
                    send_event(ws, queued_message['event'], queued_message['data'])
                    logger.info(f"重发队列消息给 {sid}: {queued_message['event']}")
                except Exception as e:
                    logger.error(f"重发队列消息失败: {str(e)}")
            sessions[sid]['message_queue'] = []
    
    logger.debug(f"收到心跳消息: {user_id}")
    send_event(ws, 'heartbeat_response', {'status': 'alive', 'timestamp': time.time()})

def is_authenticated(sid, user_id):
    """检查用户是否已认证"""
    return (sid in sessions and 
            sessions[sid].get('authenticated') and 
            sessions[sid].get('user_id') == user_id)

def send_event(ws, event_name, data):
    """发送事件消息"""
    try:
        message = f'42["{event_name}",{json.dumps(data, ensure_ascii=False)}]'
        ws.send(message)
        logger.debug(f"发送事件: {event_name}, 数据: {json.dumps(data, ensure_ascii=False)}")
        return True
    except Exception as e:
        logger.error(f"发送事件失败: {str(e)}")
        return False

def send_error(ws, code, message):
    """发送错误消息"""
    error_data = {'code': code, 'message': message}
    send_event(ws, 'error', error_data)
    logger.warning(f"发送错误: {code} - {message}")

def broadcast_to_room(room_name, event_name, data):
    """广播消息到房间"""
    if room_name not in rooms:
        logger.warning(f"房间不存在: {room_name}")
        return
    
    if event_name == 'new_message' and data.get('type') == 'message':
        try:
            from database import get_db, WechatContact
            from datetime import datetime
            
            wechat_id = room_name.replace('wechat_', '') if room_name.startswith('wechat_') else None
            contact_id = data.get('sender', {}).get('id') if data.get('sender') else None
            
            if wechat_id and contact_id:
                db = next(get_db())
                try:
                    try:
                        contact_id_int = int(contact_id)
                        contact = db.query(WechatContact).filter(
                            WechatContact.id == contact_id_int
                        ).first()
                    except (ValueError, TypeError):
                        contact = db.query(WechatContact).filter(
                            WechatContact.wechat_id == contact_id
                        ).first()
                    
                    if contact:
                        contact.last_active_at = datetime.now()
                        contact.unread_count = contact.unread_count + 1
                        db.commit()
                        logger.info(f"更新联系人 {contact_id} 的最后活动时间和未读计数")
                finally:
                    db.close()
        except Exception as e:
            logger.error(f"更新联系人活动时间和未读计数失败: {str(e)}")
        
    for sid in rooms[room_name]:
        if sid in sessions:
            try:
                ws = sessions[sid].get('ws')
                if ws:
                    success = send_event(ws, event_name, data)
                    if not success and event_name == 'new_message':
                        if 'message_queue' not in sessions[sid]:
                            sessions[sid]['message_queue'] = []
                        sessions[sid]['message_queue'].append({
                            'event': event_name,
                            'data': data,
                            'timestamp': time.time()
                        })
                        logger.info(f"消息加入队列: {sid}")
            except Exception as e:
                logger.error(f"广播消息到会话 {sid} 出错: {str(e)}")

def cleanup_inactive_sessions():
    """清理不活跃的会话"""
    current_time = time.time()
    inactive_sids = []
    
    for sid, session_data in sessions.items():
        last_heartbeat = session_data.get('last_heartbeat', 0)
        if current_time - last_heartbeat > 60:
            inactive_sids.append(sid)
    
    for sid in inactive_sids:
        logger.info(f"清理不活跃会话: {sid}")
        cleanup_session(sid)

def start_cleanup_thread():
    """启动清理线程"""
    def cleanup_loop():
        while True:
            time.sleep(30)
            cleanup_inactive_sessions()
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    logger.info("启动会话清理线程")

if __name__ == '__main__':
    from eventlet import wsgi
    from eventlet import websocket
    
    start_cleanup_thread()
    
    @websocket.WebSocketWSGI
    def websocket_handler(environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/socket.io/'):
            return handle_websocket
        return None
    
    def http_handler(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b'WebSocket Server Running']
    
    def dispatch(environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/socket.io/'):
            handler = websocket_handler(environ, start_response)
            if handler:
                return handler
        return http_handler(environ, start_response)
    
    logger.info('启动直接Socket.IO服务器，端口 5001...')
    wsgi.server(eventlet.listen(('0.0.0.0', 5001)), dispatch)
