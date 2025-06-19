# WebSocket双向通信实现文档

本文档描述了微信客户端(A端)和Web后台(B端)之间通过WebSocket实现的双向通信功能。

## 实现概述

### 1. 服务器端实现 (app.py)

- 使用Flask-SocketIO实现WebSocket服务器
- 配置async_mode为'eventlet'以避免Werkzeug错误
- 实现用户认证和房间管理机制
- 使用"wechat_{wechat_id}"格式的房间名进行消息路由
- 添加send_direct_message事件处理函数支持直接消息发送

### 2. 前端实现 (user_contacts.html, contacts.js)

- 添加WebSocket客户端连接和事件处理
- 修改sendMessage函数支持WebSocket和HTTP API两种发送方式
- 添加WebSocket切换开关，允许用户选择消息发送方式
- 保留AI回复功能，与WebSocket消息发送并存

### 3. 客户端实现 (wechat_client_example.py)

- 实现完整的WebSocket客户端
- 支持认证、心跳、消息确认和重连机制
- 实现联系人同步功能
- 处理接收到的消息并执行相应操作

## 核心功能

### 1. 用户认证和房间管理

```javascript
// 前端认证
socket.emit('authenticate', { user_id: userId });

// 加入微信房间
socket.emit('join_wechat_room', { user_id: userId, wechat_id: wechatId });
```

```python
# 后端认证处理
@socketio.on('authenticate')
def handle_authenticate(data):
    user_id = data.get('user_id')
    # 验证用户并存储socket连接
    user_socket_map[user_id] = request.sid
    emit('auth_success', {'user_id': user_id})

# 加入微信房间
@socketio.on('join_wechat_room')
def handle_join_wechat_room(data):
    user_id = data.get('user_id')
    wechat_id = data.get('wechat_id')
    room_id = f"wechat_{wechat_id}"
    join_room(room_id)
    emit('joined_wechat_room', {'wechat_id': wechat_id})
```

### 2. 联系人同步

```python
# 客户端同步联系人
def sync_contacts(self):
    wechat_ids = self.get_wechat_ids()
    for wechat_id in wechat_ids:
        contacts = self.get_local_contacts(wechat_id)
        self.sio.emit('sync_contacts', {
            'user_id': self.user_id,
            'wechat_id': wechat_id,
            'contacts': contacts
        })
```

```python
# 服务器处理联系人同步
@socketio.on('sync_contacts')
def handle_sync_contacts(data):
    user_id = data.get('user_id')
    wechat_id = data.get('wechat_id')
    contacts = data.get('contacts', [])
    # 存储联系人数据到数据库
    # ...
    emit('contacts_synced', {'sync_count': len(contacts)})
```

### 3. 消息路由

```python
# 发送直接消息
@socketio.on('send_direct_message')
def handle_send_direct_message(data):
    user_id = data.get('user_id')
    wechat_id = data.get('wechat_id')
    contact_id = data.get('contact_id')
    content = data.get('content')
    content_type = data.get('content_type', 'text')
    
    # 构建消息数据
    message_data = {
        'id': f"{user_id}_{int(time.time()*1000)}_{hash(content)}",
        'wechat_id': wechat_id,
        'contact_id': contact_id,
        'content': content,
        'content_type': content_type,
        'created_at': datetime.now().isoformat(),
        'require_ack': True
    }
    
    # 发送到对应的微信房间
    room_id = f"wechat_{wechat_id}"
    socketio.emit('new_message', message_data, to=room_id)
```

### 4. 心跳机制和断线重连

```python
# 客户端心跳发送
def _heartbeat_task(self):
    while self.running:
        if self.connected:
            self.sio.emit('heartbeat', {'user_id': self.user_id})
        time.sleep(15)  # 15秒发送一次心跳
```

```python
# 服务器心跳处理
@socketio.on('heartbeat')
def handle_heartbeat(data):
    user_id = data.get('user_id')
    emit('heartbeat_ack', {'timestamp': datetime.now().isoformat()})
```

### 5. 消息确认机制

```python
# 客户端确认消息
def acknowledge_message(self, message_id):
    self.sio.emit('message_ack', {
        'user_id': self.user_id,
        'message_id': message_id
    })
```

```python
# 服务器处理消息确认
@socketio.on('message_ack')
def handle_message_ack(data):
    user_id = data.get('user_id')
    message_id = data.get('message_id')
    # 更新消息状态为已确认
    # ...
```

## 测试方法

### 1. 测试WebSocket直接消息发送

使用test_direct_message.py脚本测试WebSocket直接消息发送功能：

```bash
python test_direct_message.py
```

### 2. 测试完整客户端功能

使用wechat_client_example.py脚本测试完整的WebSocket客户端功能：

```bash
python wechat_client_example.py
```

### 3. 前端测试

1. 启动应用服务器：`python app.py`
2. 打开浏览器访问用户联系人页面
3. 选择一个微信账号和联系人
4. 确保"使用WebSocket"开关已开启
5. 发送消息测试WebSocket功能

## 注意事项

1. 确保安装了所有必要的依赖：
   ```bash
   pip install flask flask-socketio eventlet pymysql
   ```

2. 确保async_mode设置为'eventlet'以避免Werkzeug错误：
   ```python
   socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
   ```

3. 使用socketio.run()而不是app.run()启动服务器：
   ```python
   if __name__ == '__main__':
       socketio.run(app, host='0.0.0.0', port=5000)
   ```

4. 保持现有HTTP API功能不变，确保AI回复功能与WebSocket消息发送并存。

## 总结

通过实现WebSocket双向通信功能，系统现在支持：

1. B端（Web后台）通过WebSocket向A端（微信客户端）发送消息
2. A端向B端推送事件和状态更新
3. 联系人自动同步
4. 心跳机制确保连接稳定性
5. 消息确认机制确保消息可靠传递

同时保留了原有的HTTP API接口和AI自动回复功能，使系统更加灵活和强大。
