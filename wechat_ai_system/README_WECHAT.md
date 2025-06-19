# 微信聊天机器人系统使用指南

本文档介绍了如何使用和配置微信聊天机器人系统，该系统支持用户管理多个微信账号、联系人管理、消息发送和WebSocket实时通信功能。

## 功能概述

微信聊天机器人系统具有以下特点：

1. **多微信账号管理**：每个用户可以管理多个微信账号
2. **联系人管理**：支持查看和管理微信联系人（好友和群组）
3. **消息发送**：支持发送文本和图片消息，支持定时发送和群发
4. **AI自动回复**：为每个联系人单独设置AI回复策略
5. **关键词过滤**：支持设置关键词触发特定回复
6. **WebSocket实时通信**：服务器可主动推送消息到本地微信客户端

## 系统配置

### 环境要求

- Python 3.7+
- MySQL或SQLite数据库
- Redis（可选，用于WebSocket消息队列）

### 安装依赖

```bash
pip install -r requirements.txt
pip install flask-socketio==5.3.6 redis==4.5.4 eventlet==0.33.3 pillow==10.0.0 jsonschema
```

### 配置数据库

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

### 初始化数据库

```bash
python update_db.py
```

### 创建演示账户

```bash
python create_demo_admin.py
python create_demo_data.py
```

## 启动系统

### 开发环境

```bash
python app.py
```

### 生产环境

```bash
gunicorn -k eventlet -w 1 app:app -b 0.0.0.0:5000
```

## 用户后台功能

### 登录用户后台

1. 访问 `http://服务器地址:5000/user/login`
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

### WebSocket连接

本地微信客户端需要通过WebSocket连接到服务器，以接收实时消息推送。以下是Python示例代码：

```python
import socketio

# 创建SocketIO客户端
sio = socketio.Client()

# 连接事件
@sio.event
def connect():
    print("已连接到服务器")
    # 连接后进行认证
    sio.emit('authenticate', {'user_id': '用户ID'})

# 认证成功事件
@sio.on('authenticated')
def on_authenticated(data):
    print(f"认证成功: {data}")

# 接收新消息事件
@sio.on('new_message')
def on_new_message(data):
    print(f"收到新消息: {data}")
    # 处理消息，调用本地微信API发送消息

# 连接到服务器
sio.connect('http://服务器地址:5000')
```

### 心跳机制

为保持WebSocket连接的稳定性，建议实现心跳机制：

```python
import threading
import time

def heartbeat_task():
    while True:
        try:
            sio.emit('heartbeat', {'user_id': '用户ID', 'timestamp': time.time()})
            print("已发送心跳包")
        except Exception as e:
            print(f"发送心跳包失败: {str(e)}")
        time.sleep(15)  # 15秒发送一次心跳

# 启动心跳线程
heartbeat_thread = threading.Thread(target=heartbeat_task)
heartbeat_thread.daemon = True
heartbeat_thread.start()
```

### 完整客户端示例

系统提供了一个完整的WebSocket客户端示例，包含心跳机制、断线重连、消息队列等功能：

```bash
python wechat_client_example.py
```

您可以根据自己的需求修改此示例代码，集成到您的本地微信客户端软件中。

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
