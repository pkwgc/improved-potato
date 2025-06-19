# WebSocket双向通信实现

本项目实现了微信客户端(A端)和Web后台(B端)之间的WebSocket双向通信功能。

## 目录结构

- `socketio_server.py` - WebSocket服务器实现
- `elang_websocket_simulator.py` - 易语言WebSocket客户端模拟器
- `socketio_test_client.py` - Python Socket.IO测试客户端
- `easy_language_websocket_guide.py` - 易语言WebSocket实现指南
- `test_direct_message.py` - 直接消息发送测试脚本
- `elang_implementation_guide.md` - 易语言实现详细指南
- `requirements.txt` - 项目依赖

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 启动WebSocket服务器

```bash
python socketio_server.py
```

服务器将在5000端口启动，支持WebSocket连接。

### 2. 测试WebSocket连接

使用Python测试客户端:

```bash
python socketio_test_client.py
```

或使用易语言模拟器:

```bash
python elang_websocket_simulator.py
```

### 3. 易语言客户端实现

请参考`elang_implementation_guide.md`文件，其中包含了在易语言中实现WebSocket客户端的详细步骤和代码示例。

## 通信协议

### 认证流程

1. 建立WebSocket连接: `ws://服务器地址:端口/socket.io/?EIO=4&transport=websocket`
2. 发送认证消息: `42["authenticate",{"user_id":"用户ID"}]`
3. 加入微信房间: `42["join_wechat_room",{"user_id":"用户ID","wechat_id":"微信ID"}]`

### 消息格式

- 发送消息: `42["send_direct_message",{"user_id":"用户ID","wechat_id":"微信ID","contact_id":"联系人ID","content":"消息内容","content_type":"text"}]`
- 确认消息: `42["message_ack",{"user_id":"用户ID","message_id":"消息ID"}]`
- 心跳包: `2` (单个数字)

## 注意事项

- 消息格式必须严格遵循Socket.IO协议，特别是前缀"42"和JSON格式
- 心跳包必须是单个数字"2"
- 易语言客户端需要正确处理WebSocket握手和消息格式
