"""
Socket.IO测试客户端
使用python-socketio库实现WebSocket连接
用于测试与Socket.IO服务器的通信
"""
import socketio
import time
import logging
import json
import threading
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_URL = 'http://localhost:5000'
USER_ID = 'test'
WECHAT_ID_A = 'wechat_A'
WECHAT_ID_B = 'wechat_B'
CONTACT_ID = 'test_contact'

class SocketIOTestClient:
    def __init__(self, user_id, wechat_id, name):
        self.user_id = user_id
        self.wechat_id = wechat_id
        self.name = name
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.connected = False
        self.authenticated = False
        self.joined_room = False
        self.running = True
        self.messages_received = []
        
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.sio.event
        def connect():
            self.connected = True
            logger.info(f"[{self.name}] 已连接到服务器: {SERVER_URL}")
            
            self.sio.emit('authenticate', {'user_id': self.user_id})
            logger.info(f"[{self.name}] 发送认证消息: user_id={self.user_id}")

        @self.sio.event
        def disconnect():
            self.connected = False
            self.authenticated = False
            self.joined_room = False
            logger.info(f"[{self.name}] 与服务器断开连接")

        @self.sio.event
        def connect_error(data):
            logger.error(f"[{self.name}] 连接错误: {data}")

        @self.sio.on('auth_success')
        def on_auth_success(data):
            self.authenticated = True
            logger.info(f"[{self.name}] 认证成功: {data}")
            
            self.sio.emit('join_wechat_room', {
                'user_id': self.user_id,
                'wechat_id': self.wechat_id
            })
            logger.info(f"[{self.name}] 请求加入房间: wechat_id={self.wechat_id}")

        @self.sio.on('joined_wechat_room')
        def on_joined_wechat_room(data):
            self.joined_room = True
            logger.info(f"[{self.name}] 已加入微信房间: {data}")

        @self.sio.on('new_message')
        def on_new_message(data):
            self.messages_received.append(data)
            logger.info(f"[{self.name}] 收到新消息: {json.dumps(data, ensure_ascii=False)}")
            
            if data.get('id') and data.get('require_ack', False):
                self.sio.emit('message_ack', {
                    'user_id': self.user_id,
                    'message_id': data.get('id')
                })
                logger.info(f"[{self.name}] 已确认消息: {data.get('id')}")

        @self.sio.on('error')
        def on_error(data):
            logger.error(f"[{self.name}] 收到错误: {json.dumps(data, ensure_ascii=False)}")

        @self.sio.on('heartbeat_response')
        def on_heartbeat_response(data):
            logger.debug(f"[{self.name}] 收到心跳响应: {json.dumps(data, ensure_ascii=False)}")

    def connect_to_server(self):
        try:
            logger.info(f"[{self.name}] 正在连接到服务器: {SERVER_URL}")
            self.sio.connect(SERVER_URL)
            return True
        except Exception as e:
            logger.error(f"[{self.name}] 连接失败: {str(e)}")
            return False
    
    def send_heartbeat(self):
        while self.running and self.connected:
            if self.connected:
                logger.debug(f"[{self.name}] 发送心跳")
                self.sio.emit('heartbeat', {'user_id': self.user_id})
            time.sleep(15)
    
    def disconnect_from_server(self):
        self.running = False
        if self.connected:
            self.sio.disconnect()
            logger.info(f"[{self.name}] 客户端已停止")

def test_precise_targeting():
    """测试精确推送功能"""
    logger.info("开始测试精确推送功能")
    
    client_a = SocketIOTestClient(USER_ID, WECHAT_ID_A, "微信A客户端")
    client_b = SocketIOTestClient(USER_ID, WECHAT_ID_B, "微信B客户端")
    
    try:
        if not client_a.connect_to_server():
            logger.error("微信A客户端连接失败")
            return False
            
        if not client_b.connect_to_server():
            logger.error("微信B客户端连接失败")
            return False
        
        heartbeat_a = threading.Thread(target=client_a.send_heartbeat, daemon=True)
        heartbeat_b = threading.Thread(target=client_b.send_heartbeat, daemon=True)
        heartbeat_a.start()
        heartbeat_b.start()
        
        time.sleep(3)
        
        if not (client_a.joined_room and client_b.joined_room):
            logger.error("客户端未能成功加入房间")
            return False
        
        logger.info("开始测试消息发送...")
        
        client_a.sio.emit('send_direct_message', {
            'user_id': USER_ID,
            'wechat_id': WECHAT_ID_A,
            'contact_id': CONTACT_ID,
            'content': f"测试消息发送到微信A - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'content_type': 'text'
        })
        
        time.sleep(2)
        
        client_b.sio.emit('send_direct_message', {
            'user_id': USER_ID,
            'wechat_id': WECHAT_ID_B,
            'contact_id': CONTACT_ID,
            'content': f"测试消息发送到微信B - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'content_type': 'text'
        })
        
        time.sleep(5)
        
        logger.info(f"微信A收到消息数量: {len(client_a.messages_received)}")
        logger.info(f"微信B收到消息数量: {len(client_b.messages_received)}")
        
        success = True
        for msg in client_a.messages_received:
            if msg.get('receiver', {}).get('id') != CONTACT_ID:
                logger.error(f"微信A收到了不应该收到的消息: {msg}")
                success = False
        
        for msg in client_b.messages_received:
            if msg.get('receiver', {}).get('id') != CONTACT_ID:
                logger.error(f"微信B收到了不应该收到的消息: {msg}")
                success = False
        
        if success:
            logger.info("✅ 精确推送测试通过")
        else:
            logger.error("❌ 精确推送测试失败")
        
        return success
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        return False
    finally:
        client_a.disconnect_from_server()
        client_b.disconnect_from_server()

if __name__ == "__main__":
    test_precise_targeting()
