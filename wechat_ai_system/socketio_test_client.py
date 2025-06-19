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

SERVER_URL = 'http://localhost:5000'  # 服务器地址
USER_ID = 'pk_wgc'  # 用户ID
WECHAT_ID = 'pk_wgc'  # 微信ID
CONTACT_ID = 'J1206233446'  # 联系人ID

sio = socketio.Client(logger=True, engineio_logger=True)

connected = False
authenticated = False
joined_room = False
running = True

@sio.event
def connect():
    """连接成功事件处理"""
    global connected
    connected = True
    logger.info(f"已连接到服务器: {SERVER_URL}")
    
    sio.emit('authenticate', {'user_id': USER_ID})
    logger.info(f"发送认证消息: user_id={USER_ID}")

@sio.event
def disconnect():
    """断开连接事件处理"""
    global connected, authenticated, joined_room
    connected = False
    authenticated = False
    joined_room = False
    logger.info("与服务器断开连接")

@sio.event
def connect_error(data):
    """连接错误事件处理"""
    logger.error(f"连接错误: {data}")

@sio.on('auth_success')
def on_auth_success(data):
    """认证成功事件处理"""
    global authenticated
    authenticated = True
    logger.info(f"认证成功: {data}")
    
    sio.emit('join_wechat_room', {
        'user_id': USER_ID,
        'wechat_id': WECHAT_ID
    })
    logger.info(f"请求加入房间: wechat_id={WECHAT_ID}")

@sio.on('joined_wechat_room')
def on_joined_wechat_room(data):
    """加入房间成功事件处理"""
    global joined_room
    joined_room = True
    logger.info(f"已加入微信房间: {data}")
    
    send_test_message()

@sio.on('message_sent')
def on_message_sent(data):
    """消息发送成功事件处理"""
    logger.info(f"消息发送成功: {json.dumps(data, ensure_ascii=False)}")

@sio.on('new_message')
def on_new_message(data):
    """收到新消息事件处理"""
    logger.info(f"收到新消息: {json.dumps(data, ensure_ascii=False)}")
    
    if data.get('id') and data.get('require_ack', False):
        sio.emit('message_ack', {
            'user_id': USER_ID,
            'message_id': data.get('id')
        })
        logger.info(f"已确认消息: {data.get('id')}")

@sio.on('error')
def on_error(data):
    """错误事件处理"""
    logger.error(f"收到错误: {json.dumps(data, ensure_ascii=False)}")

@sio.on('heartbeat_response')
def on_heartbeat_response(data):
    """心跳响应事件处理"""
    logger.debug(f"收到心跳响应: {json.dumps(data, ensure_ascii=False)}")

@sio.on('ack_received')
def on_ack_received(data):
    """消息确认接收事件处理"""
    logger.info(f"消息确认已接收: {json.dumps(data, ensure_ascii=False)}")

def send_test_message():
    """发送测试消息"""
    logger.info(f"发送测试消息到联系人 {CONTACT_ID}")
    
    sio.emit('send_direct_message', {
        'user_id': USER_ID,
        'wechat_id': WECHAT_ID,
        'contact_id': CONTACT_ID,
        'content': f"测试消息 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        'content_type': 'text'
    })

def send_heartbeat():
    """发送心跳"""
    while running:
        if connected:
            logger.debug("发送心跳")
            sio.emit('heartbeat', {'user_id': USER_ID})
        time.sleep(15)  # 15秒发送一次心跳

def main():
    """主函数"""
    global running
    
    try:
        heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        logger.info(f"正在连接到服务器: {SERVER_URL}")
        sio.connect(SERVER_URL)
        
        logger.info("运行60秒...")
        time.sleep(60)
        
        sio.disconnect()
        logger.info("客户端已停止")
        
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    finally:
        running = False

if __name__ == "__main__":
    main()
