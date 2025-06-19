# 微信聊天机器人系统使用指南

## 系统概述

微信聊天机器人系统是一个基于Flask和WebSocket的应用，支持用户管理多个微信账号、联系人管理、消息发送和AI自动回复等功能。系统分为服务器端和客户端两部分：

1. **服务器端**：提供Web界面、API接口和WebSocket服务
2. **客户端**：本地微信软件，通过WebSocket与服务器通信

## 系统功能

1. **多微信账号管理**：每个用户可以管理多个微信账号
2. **联系人管理**：支持查看和管理微信联系人（好友和群组）
3. **消息发送**：支持发送文本和图片消息，支持定时发送和群发
4. **AI自动回复**：为每个联系人单独设置AI回复策略
5. **关键词过滤**：支持设置关键词触发特定回复
6. **WebSocket实时通信**：服务器可主动推送消息到本地微信客户端

## 安装部署

### 系统要求

- Python 3.7+
- MySQL或SQLite数据库
- Redis（可选，用于WebSocket消息队列）

### 安装步骤

1. **解压源码包**
   ```bash
   unzip wechat_system_package.zip
   cd wechat_system_package
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   pip install flask-socketio==5.3.6 redis==4.5.4 eventlet==0.33.3 pillow==10.0.0 jsonschema
   ```

3. **配置数据库**
   - SQLite模式（开发环境）：
     创建`.env`文件，添加：
     ```
     USE_SQLITE=true
     SECRET_KEY=your_secret_key
     DEBUG=true
     ```
   
   - MySQL模式（生产环境）：
     创建`.env`文件，添加：
     ```
     DATABASE_URL=mysql+pymysql://用户名:密码@数据库地址/数据库名
     SECRET_KEY=your_secret_key
     DEBUG=false
     ```

4. **创建必要目录**
   ```bash
   mkdir -p logs uploads chat_records
   ```

5. **初始化数据库**
   ```bash
   python update_db.py
   ```

6. **创建演示账户**
   ```bash
   python create_demo_admin.py
   python create_demo_data.py
   ```

7. **启动应用**
   - 开发环境：
     ```bash
     python app.py
     ```
   
   - 生产环境（使用gunicorn）：
     ```bash
     pip install gunicorn
     gunicorn -k eventlet -w 1 app:app -b 0.0.0.0:5000
     ```

8. **访问系统**
   - 浏览器打开：`http://服务器IP:5000/user/login`
   - 使用演示账户登录：
     - 用户名：`demo_user`
     - 密码：`demo123`

### 快速部署（演示环境）

系统提供了一个快速部署脚本，可以一键部署演示环境：

```bash
chmod +x deploy_demo.sh
./deploy_demo.sh
```

## 使用指南

### 用户登录

1. 访问 `http://服务器IP:5000/user/login`
2. 输入用户名和密码登录

### 管理微信账号

1. 登录后，点击左侧菜单的"联系人管理"
2. 在页面顶部的"选择微信账号"下拉菜单中选择要管理的微信账号
3. 点击"添加微信账号"按钮可以添加新的微信账号

### 管理联系人

1. 选择微信账号后，系统会显示该账号的联系人列表
2. 可以使用搜索框搜索联系人
3. 可以切换显示好友或群组
4. 点击联系人可以查看详情和进行操作

### 发送消息

1. 在联系人详情页面，可以发送文本或图片消息
2. 支持定时发送功能
3. 点击"群发消息"按钮可以向多个联系人发送相同消息

### 设置AI自动回复

1. 在联系人详情页面，可以启用或禁用AI自动回复
2. 可以选择不同的AI回复策略
3. 可以启用关键词过滤功能
4. 可以添加和管理关键词过滤规则

## 本地微信客户端集成

### WebSocket客户端示例

系统提供了一个完整的WebSocket客户端示例（`wechat_client_example.py`），包含心跳机制、断线重连、消息队列等功能。您可以根据自己的需求修改此示例代码，集成到您的本地微信客户端软件中。

### 集成步骤

1. **复制WebSocket客户端示例代码**
   将`wechat_client_example.py`文件复制到您的本地微信客户端项目中。

2. **安装依赖**
   ```bash
   pip install socketio==5.3.6 requests
   ```

3. **修改配置**
   修改`wechat_client_example.py`中的配置：
   ```python
   server_url = "http://服务器IP:5000"  # WebSocket服务器URL
   user_id = "您的用户ID"  # 用户ID
   ```

4. **集成到您的微信客户端**
   在您的微信客户端代码中导入并使用WebSocket客户端：
   ```python
   from wechat_client_example import WeChatClient
   
   # 创建WebSocket客户端
   client = WeChatClient(server_url="http://服务器IP:5000", user_id="您的用户ID")
   
   # 启动客户端
   client.run()
   ```

5. **自定义消息处理**
   修改`handle_message`方法以适应您的微信API：
   ```python
   def handle_message(self, data):
       message_type = data.get('content_type', 'text')
       contact_id = data.get('contact_id')
       content = data.get('content')
       
       if message_type == 'text':
           # 调用您的微信API发送文本消息
           your_wechat_api.send_text(contact_id, content)
       elif message_type == 'image':
           # 调用您的微信API发送图片消息
           your_wechat_api.send_image(contact_id, content)
   ```

### 心跳机制

WebSocket客户端示例中已经实现了心跳机制，每15秒发送一次心跳包，确保连接稳定：

```python
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
```

### 断线重连

WebSocket客户端示例中已经实现了断线重连机制，当连接断开时会自动尝试重新连接：

```python
self.sio = socketio.Client(reconnection=True, reconnection_attempts=10, reconnection_delay=1, reconnection_delay_max=5)
```

### 消息队列

WebSocket客户端示例中已经实现了消息队列，当消息发送失败时会将消息加入队列，稍后重试：

```python
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
```

## API接口

### 同步联系人

```
POST /api/sync_contacts
Content-Type: application/json

{
  "owner_id": "微信账号ID",
  "contacts": [
    {
      "wechat_id": "联系人微信ID",
      "nickname": "昵称",
      "remark": "备注",
      "is_group": false,
      "avatar": "头像Base64"
    }
  ]
}
```

### 获取联系人列表

```
GET /api/contacts?owner_id=微信账号ID&is_group=false&search=关键词
```

### 发送消息

```
POST /api/send_message
Content-Type: application/json

{
  "owner_id": "微信账号ID",
  "contact_ids": ["联系人ID1", "联系人ID2"],
  "content": "消息内容",
  "content_type": "text",
  "scheduled_time": "2025-05-24T10:00:00Z"  // 可选
}
```

### 设置AI回复

```
POST /api/set_ai_reply
Content-Type: application/json

{
  "owner_id": "微信账号ID",
  "contact_id": "联系人ID",
  "ai_reply_enabled": true,
  "ai_strategy_id": 1,
  "keyword_filter_enabled": false
}
```

## WebSocket事件

### 客户端事件

1. **连接**
   ```javascript
   socket.on('connect', function() {
     console.log('已连接到服务器');
   });
   ```

2. **认证**
   ```javascript
   socket.emit('authenticate', { user_id: '用户ID' });
   ```

3. **加入房间**
   ```javascript
   socket.emit('join', { user_id: '用户ID' });
   ```

4. **心跳**
   ```javascript
   socket.emit('heartbeat', { user_id: '用户ID', timestamp: new Date().toISOString() });
   ```

### 服务器事件

1. **认证成功**
   ```javascript
   socket.on('authenticated', function(data) {
     console.log('认证成功:', data);
   });
   ```

2. **新消息**
   ```javascript
   socket.on('new_message', function(data) {
     console.log('收到新消息:', data);
     // 处理新消息...
   });
   ```

3. **错误**
   ```javascript
   socket.on('error', function(data) {
     console.error('收到错误:', data);
   });
   ```

## 故障排除

### 登录循环问题

如果遇到登录后仍然返回登录页面的问题：

1. 检查浏览器是否启用了Cookie
2. 清除浏览器缓存和Cookie
3. 确认服务器会话配置正确

### WebSocket连接问题

如果本地客户端无法连接到WebSocket服务器：

1. 确认服务器地址和端口正确
2. 检查防火墙是否允许WebSocket连接
3. 确认服务器已启用WebSocket功能（ENABLE_SOCKET_IO=True）

### 消息发送失败

如果消息发送失败：

1. 检查联系人ID是否正确
2. 确认微信账号ID正确
3. 查看服务器日志中是否有错误信息

## 注意事项

1. 本系统仅提供服务器端功能，需要配合本地微信客户端软件使用
2. 本地微信客户端软件需要实现WebSocket客户端功能，以接收服务器推送的消息
3. 本系统不提供微信API接口，需要用户自行实现微信消息发送功能
4. 建议在生产环境中使用HTTPS协议，以保证通信安全
5. 心跳机制是保持WebSocket连接稳定的有效方法，建议保留并根据实际网络环境调整心跳间隔
