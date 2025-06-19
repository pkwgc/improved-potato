#!/usr/bin/env python

"""
微信客户端WebSocket连接示例
用于演示本地微信软件如何通过WebSocket接收后台发送的消息
"""

import time
import json
import logging
import threading
import socketio
import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wechat_client.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WeChatClient")

class WeChatClient:
    """微信客户端WebSocket连接示例"""
    
    def __init__(self, server_url, user_id, api_key=None):
        """
        初始化微信客户端
        
        Args:
            server_url: WebSocket服务器URL
            user_id: 用户ID
            api_key: API密钥（如果需要）
        """
        self.server_url = server_url
        self.user_id = user_id
        self.api_key = api_key
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=10, reconnection_delay=1, reconnection_delay_max=5)
        self.connected = False
        self.message_queue = []
        self.message_history = {}  # 用于消息去重
        self.setup_socketio()
        self.heartbeat_thread = None
        self.running = False
    
    def setup_socketio(self):
        """设置SocketIO事件处理"""
        
        @self.sio.event
        def connect():
            """连接成功事件"""
            logger.info(f"已连接到服务器: {self.server_url}")
            self.connected = True
            self.authenticate()
            self.process_message_queue()
        
        @self.sio.event
        def disconnect():
            """断开连接事件"""
            logger.warning("与服务器断开连接")
            self.connected = False
        
        @self.sio.event
        def connect_error(data):
            """连接错误事件"""
            logger.error(f"连接错误: {data}")
            self.connected = False
        
        @self.sio.on('authenticated')
        def on_authenticated(data):
            """认证成功事件"""
            logger.info(f"认证成功: {data}")
            self.sio.emit('join', {'user_id': self.user_id})
            self.join_wechat_rooms()
            self.sync_contacts()
        
        @self.sio.on('joined_wechat_room')
        def on_joined_wechat_room(data):
            """加入微信房间事件"""
            logger.info(f"已加入微信房间: {data}")
            wechat_id = data.get('wechat_id')
            if wechat_id:
                logger.info(f"成功加入微信账号 {wechat_id} 的房间")
        
        @self.sio.on('contacts_synced')
        def on_contacts_synced(data):
            """联系人同步完成事件"""
            logger.info(f"联系人同步完成: {data}")
            sync_count = data.get('sync_count', 0)
            logger.info(f"成功同步 {sync_count} 个联系人")
        
        @self.sio.on('contacts_updated')
        def on_contacts_updated(data):
            """联系人更新事件"""
            logger.info(f"联系人已更新: {data}")
        
        @self.sio.on('heartbeat_ack')
        def on_heartbeat_ack(data):
            """心跳确认事件"""
            logger.debug(f"收到心跳确认: {data}")
        
        @self.sio.on('new_message')
        def on_new_message(data):
            """接收新消息事件"""
            logger.info(f"收到新消息: {data}")
            self.handle_message(data)
            if data.get('id') and data.get('require_ack', False):
                self.acknowledge_message(data.get('id'))
        
        @self.sio.on('broadcast_message')
        def on_broadcast_message(data):
            """接收广播消息事件"""
            logger.info(f"收到广播消息: {data}")
            self.handle_message(data)
            if data.get('id') and data.get('require_ack', False):
                self.acknowledge_message(data.get('id'))
        
        @self.sio.on('error')
        def on_error(data):
            """错误事件"""
            logger.error(f"收到错误: {data}")
            if data.get('code') == 'auth_required':
                logger.info("尝试重新认证")
                self.authenticate()
    
    def authenticate(self):
        """向服务器发送认证信息"""
        logger.info(f"发送认证信息: user_id={self.user_id}")
        self.sio.emit('authenticate', {'user_id': self.user_id})
        
    def join_wechat_rooms(self):
        """加入微信账号房间"""
        logger.info("尝试加入微信账号房间")
        wechat_ids = self.get_wechat_ids()
        for wechat_id in wechat_ids:
            logger.info(f"请求加入微信账号 {wechat_id} 的房间")
            self.sio.emit('join_wechat_room', {
                'user_id': self.user_id,
                'wechat_id': wechat_id
            })
            
    def get_wechat_ids(self):
        """获取用户的微信账号列表"""
        return ["demo_wechat"]
        
    def sync_contacts(self):
        """同步联系人信息到服务器"""
        logger.info("开始同步联系人信息")
        wechat_ids = self.get_wechat_ids()
        
        for wechat_id in wechat_ids:
            contacts = self.get_local_contacts(wechat_id)
            
            logger.info(f"通过WebSocket同步 {len(contacts)} 个联系人")
            self.sio.emit('sync_contacts', {
                'user_id': self.user_id,
                'wechat_id': wechat_id,
                'contacts': contacts
            })
            
    def get_local_contacts(self, wechat_id):
        """获取本地联系人列表（示例）"""
        return [
            {
                "wechat_id": "friend1",
                "nickname": "张三",
                "remark": "老张",
                "avatar": "base64://...",
                "is_group": False
            },
            {
                "wechat_id": "group1",
                "nickname": "家庭群",
                "remark": "",
                "avatar": "base64://...",
                "is_group": True,
                "member_count": 5
            }
        ]
        
    def acknowledge_message(self, message_id):
        """确认消息已接收"""
        logger.debug(f"确认消息: {message_id}")
        self.sio.emit('message_ack', {
            'user_id': self.user_id,
            'message_id': message_id
        })
    
    def connect(self):
        """连接到WebSocket服务器"""
        if not self.connected:
            try:
                logger.info(f"正在连接到服务器: {self.server_url}")
                self.sio.connect(self.server_url)
            except Exception as e:
                logger.error(f"连接失败: {str(e)}")
                return False
        return True
    
    def disconnect(self):
        """断开与WebSocket服务器的连接"""
        if self.connected:
            try:
                self.sio.disconnect()
                logger.info("已断开与服务器的连接")
            except Exception as e:
                logger.error(f"断开连接失败: {str(e)}")
    
    def start_heartbeat(self):
        """启动心跳线程"""
        if self.heartbeat_thread is None or not self.heartbeat_thread.is_alive():
            self.running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_task)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            logger.info("心跳线程已启动")
    
    def stop_heartbeat(self):
        """停止心跳线程"""
        self.running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1)
            logger.info("心跳线程已停止")
    
    def _heartbeat_task(self):
        """心跳任务"""
        while self.running:
            if self.connected:
                try:
                    self.sio.emit('heartbeat', {'user_id': self.user_id, 'timestamp': datetime.now().isoformat()})
                    logger.debug("已发送心跳包")
                except Exception as e:
                    logger.error(f"发送心跳包失败: {str(e)}")
            time.sleep(15)  # 15秒发送一次心跳
    
    def handle_message(self, data):
        """
        处理接收到的消息
        
        Args:
            data: 消息数据
        """
        message_id = data.get('id')
        if message_id and message_id in self.message_history:
            logger.info(f"忽略重复消息: {message_id}")
            return
        
        if message_id:
            self.message_history[message_id] = datetime.now()
            if len(self.message_history) > 1000:
                oldest_keys = sorted(self.message_history.keys(), key=lambda k: self.message_history[k])[:100]
                for key in oldest_keys:
                    self.message_history.pop(key, None)
        
        message_type = data.get('content_type', 'text')
        contact_id = data.get('contact_id')
        content = data.get('content')
        
        if not contact_id or not content:
            logger.warning(f"消息缺少必要字段: {data}")
            return
        
        try:
            if message_type == 'text':
                self.send_text_message(contact_id, content)
            elif message_type == 'image':
                self.send_image_message(contact_id, content)
            else:
                logger.warning(f"不支持的消息类型: {message_type}")
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            self.message_queue.append(data)
    
    def process_message_queue(self):
        """处理消息队列中的消息"""
        if not self.connected:
            return
        
        if not self.message_queue:
            return
        
        logger.info(f"处理队列中的消息，数量: {len(self.message_queue)}")
        
        queue_copy = self.message_queue.copy()
        self.message_queue = []
        
        for message in queue_copy:
            try:
                self.handle_message(message)
            except Exception as e:
                logger.error(f"处理队列消息失败: {str(e)}")
                self.message_queue.append(message)
    
    def send_text_message(self, contact_id, content):
        """
        发送文本消息到微信
        
        Args:
            contact_id: 联系人ID
            content: 消息内容
        """
        logger.info(f"发送文本消息到 {contact_id}: {content}")
        
        logger.info(f"文本消息发送成功")
    
    def send_image_message(self, contact_id, image_data):
        """
        发送图片消息到微信
        
        Args:
            contact_id: 联系人ID
            image_data: 图片数据（Base64或URL）
        """
        logger.info(f"发送图片消息到 {contact_id}")
        
        logger.info(f"图片消息发送成功")
    
    def run(self):
        """运行客户端"""
        try:
            if self.connect():
                self.start_heartbeat()
                
                while True:
                    try:
                        time.sleep(1)
                        if self.connected and self.message_queue:
                            self.process_message_queue()
                    except KeyboardInterrupt:
                        logger.info("接收到退出信号")
                        break
                    except Exception as e:
                        logger.error(f"运行时错误: {str(e)}")
        finally:
            self.stop_heartbeat()
            self.disconnect()
            logger.info("客户端已停止")

def main():
    """主函数"""
    server_url = "http://localhost:5000"  # WebSocket服务器URL
    user_id = "demo_user"  # 用户ID
    
    client = WeChatClient(server_url, user_id)
    
    client.run()

if __name__ == "__main__":
    main()
