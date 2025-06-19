"""
模拟易语言WebSocket客户端的Python脚本
严格按照Socket.IO协议格式发送原始消息
"""
import websocket
import threading
import time
import json
import logging
import random

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EasyLanguageWebSocketSimulator:
    def __init__(self, server_url, user_id, wechat_id, contact_id):
        self.server_url = server_url
        self.user_id = user_id
        self.wechat_id = wechat_id
        self.contact_id = contact_id
        self.ws = None
        self.connected = False
        self.authenticated = False
        self.joined_room = False
        self.running = True
        self.heartbeat_thread = None
        
    def on_message(self, ws, message):
        """处理接收到的消息"""
        logger.info(f"收到消息: {message}")
        
        if message == "2" or message == "3":
            logger.debug(f"收到心跳消息: {message}")
            return
            
        if len(message) < 1:
            logger.warning(f"消息格式错误: {message}")
            return
            
        msg_type = message[0]
        
        # 处理不同类型的消息
        if msg_type == "4" and len(message) >= 2:  # 事件消息
            try:
                if message[1] == "2":
                    # 提取JSON部分
                    json_part = message[2:]
                    data = json.loads(json_part)
                    
                    if len(data) < 2:
                        logger.warning("事件消息格式错误")
                        return
                        
                    event_name = data[0]
                    event_data = data[1]
                    
                    logger.info(f"事件名: {event_name}, 数据: {json.dumps(event_data, ensure_ascii=False)}")
                    
                    # 处理不同事件
                    if event_name == "auth_success":
                        logger.info("认证成功")
                        self.authenticated = True
                        self.join_wechat_room()
                        
                    elif event_name == "joined_wechat_room":
                        logger.info(f"已加入微信房间: {event_data}")
                        self.joined_room = True
                        
                    elif event_name == "new_message":
                        logger.info(f"收到新消息: {json.dumps(event_data, ensure_ascii=False)}")
                        # 如果消息需要确认，发送确认
                        if event_data.get('id') and event_data.get('require_ack', False):
                            self.acknowledge_message(event_data.get('id'))
                            
                    elif event_name == "error":
                        logger.error(f"收到错误: {json.dumps(event_data, ensure_ascii=False)}")
                        
                elif message[1] == "0":
                    logger.info("连接成功")
                    self.authenticate()
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {str(e)}, 消息: {message}")
                
        elif msg_type == "0":  # 握手消息
            try:
                # 提取JSON部分 (去掉第一个字符)
                json_part = message[1:]
                data = json.loads(json_part)
                logger.info(f"收到握手消息: {json.dumps(data, ensure_ascii=False)}")
                
                self.authenticate()
                
            except json.JSONDecodeError as e:
                logger.error(f"握手消息解析错误: {str(e)}, 消息: {message}")
                
        elif msg_type == "1":  # 断开连接
            logger.info("服务器断开连接")
            self.connected = False
            
    def on_error(self, ws, error):
        """处理错误"""
        logger.error(f"发生错误: {str(error)}")
        
    def on_close(self, ws, close_status_code, close_msg):
        """处理连接关闭"""
        logger.info(f"连接关闭: {close_status_code} - {close_msg}")
        self.connected = False
        self.authenticated = False
        self.joined_room = False
        
    def on_open(self, ws):
        """处理连接打开"""
        logger.info("连接已打开")
        self.connected = True
        
    def connect(self):
        """连接到WebSocket服务器"""
        # 构建Socket.IO URL
        if not self.server_url.startswith('http://') and not self.server_url.startswith('https://'):
            self.server_url = f"http://{self.server_url}"
        socket_io_url = f"ws://{self.server_url.replace('http://', '')}/socket.io/?EIO=4&transport=websocket"
        logger.info(f"正在连接到: {socket_io_url}")
        
        # 创建WebSocket连接
        self.ws = websocket.WebSocketApp(
            socket_io_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # 启动WebSocket连接线程
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
        
        # 等待连接建立
        time.sleep(2)
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_task)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        return self.connected
        
    def authenticate(self):
        """发送认证消息"""
        if not self.connected or not self.ws:
            logger.warning("未连接，无法发送认证消息")
            return False
            
        auth_data = {"user_id": self.user_id}
        auth_message = f'42["authenticate",{json.dumps(auth_data)}]'
        
        logger.info(f"发送认证消息: {auth_message}")
        try:
            self.ws.send(auth_message)
            return True
        except Exception as e:
            logger.error(f"发送认证消息失败: {str(e)}")
            return False
        
    def join_wechat_room(self):
        """加入微信房间"""
        if not self.authenticated or not self.ws:
            logger.warning("未认证或未连接，无法加入房间")
            return False
            
        room_data = {"user_id": self.user_id, "wechat_id": self.wechat_id}
        room_message = f'42["join_wechat_room",{json.dumps(room_data)}]'
        
        logger.info(f"发送加入房间消息: {room_message}")
        try:
            self.ws.send(room_message)
            return True
        except Exception as e:
            logger.error(f"发送加入房间消息失败: {str(e)}")
            return False
        
    def send_message(self, content, content_type="text"):
        """发送消息"""
        if not self.joined_room or not self.ws:
            logger.warning("未加入房间或未连接，无法发送消息")
            return False
            
        message_data = {
            "user_id": self.user_id,
            "wechat_id": self.wechat_id,
            "contact_id": self.contact_id,
            "content": content,
            "content_type": content_type
        }
        message = f'42["send_direct_message",{json.dumps(message_data, ensure_ascii=False)}]'
        
        logger.info(f"发送消息: {message}")
        try:
            self.ws.send(message)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return False
        
    def acknowledge_message(self, message_id):
        """确认消息"""
        if not self.connected or not self.ws:
            logger.warning("未连接，无法确认消息")
            return False
            
        ack_data = {"user_id": self.user_id, "message_id": message_id}
        ack_message = f'42["message_ack",{json.dumps(ack_data)}]'
        
        logger.info(f"发送消息确认: {ack_message}")
        try:
            self.ws.send(ack_message)
            return True
        except Exception as e:
            logger.error(f"发送消息确认失败: {str(e)}")
            return False
        
    def heartbeat_task(self):
        """心跳任务"""
        while self.running and self.connected:
            try:
                # 发送心跳包（必须是单个数字"2"）
                if self.connected and self.ws and self.ws.sock:
                    logger.debug("发送心跳")
                    self.ws.send("2")
            except Exception as e:
                logger.error(f"发送心跳失败: {str(e)}")
                
            # 等待15秒
            time.sleep(15)
            
    def run(self, duration=60):
        """运行模拟器一段时间"""
        if not self.connect():
            logger.error("连接失败")
            return
            
        try:
            # 等待认证和加入房间
            start_time = time.time()
            while time.time() - start_time < 10 and not self.joined_room:
                time.sleep(0.5)
                
            if not self.joined_room:
                logger.warning("10秒内未能加入房间")
                
            # 发送测试消息
            if self.joined_room:
                for i in range(3):
                    self.send_message(f"测试消息 {i+1} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    time.sleep(5)
                    
            # 运行指定时间
            logger.info(f"继续运行 {duration} 秒...")
            time.sleep(duration)
            
        except KeyboardInterrupt:
            logger.info("用户中断")
        finally:
            self.running = False
            if self.ws:
                self.ws.close()
            logger.info("模拟器已停止")

if __name__ == "__main__":
    # 使用用户提供的参数
    simulator = EasyLanguageWebSocketSimulator(
        server_url="localhost:5000",
        user_id="pk_wgc",
        wechat_id="pk_wgc",
        contact_id="J1206233446"
    )
    
    simulator.run(duration=60)  # 运行60秒
