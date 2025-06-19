# WebSocket实时通信系统测试指南

## 环境准备

1. **安装依赖**
   ```bash
   pip install flask flask-socketio eventlet python-socketio
   ```

2. **安装WebSocket客户端库（可选，但推荐）**
   ```bash
   pip install websocket-client
   ```

## 文件说明

解压`wechat_websocket_implementation.zip`后，您将获得以下文件：

- `app.py` - 主应用文件，包含WebSocket服务器实现
- `app_functions.py` - 应用功能模块，包含消息队列管理
- `api_send_message.py` - 消息发送API，集成WebSocket推送
- `cleanup_task.py` - 过期连接清理任务
- `config.py` - 配置文件
- `database.py` - 数据库模型和连接
- `test_websocket_client.py` - 测试客户端
- `wechat_client_example.py` - 客户端示例
- `README.md` - 实现文档

## 测试步骤

### 1. 启动服务器

```bash
cd wechat_websocket_package
python -m flask run --host=0.0.0.0 --port=5000
```

### 2. 测试WebSocket连接

在新的终端窗口中运行测试客户端：

```bash
cd wechat_websocket_package
python test_websocket_client.py
```

观察输出日志，确认以下功能正常工作：
- 连接建立
- 认证成功
- 心跳机制
- 断开连接

### 3. 测试联系人同步

修改`test_websocket_client.py`中的`get_local_contacts`方法，添加更多测试联系人数据，然后运行测试客户端观察同步结果。

### 4. 测试消息推送

使用以下命令发送测试消息：

```bash
curl -X POST http://localhost:5000/api/send_message \
  -H "Content-Type: application/json" \
  -d '{
    "owner_id": "test_user_123",
    "contact_ids": [1],
    "content": "测试消息",
    "content_type": "text"
  }'
```

观察测试客户端是否收到消息并发送确认。

### 5. 测试广播消息

使用以下命令发送广播消息：

```bash
curl -X POST http://localhost:5000/api/broadcast_message \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "test_user_123",
    "wechat_ids": ["test_wechat_id"],
    "content": "广播测试消息",
    "content_type": "text"
  }'
```

观察测试客户端是否收到广播消息。

## 集成到现有系统

### 1. 服务端集成

1. 将`app.py`中的WebSocket相关代码集成到您的现有Flask应用中
2. 确保导入所有必要的模块和函数
3. 初始化SocketIO并注册事件处理器

### 2. 客户端集成

1. 参考`wechat_client_example.py`中的代码，实现WebSocket客户端
2. 添加事件处理器处理服务器发送的消息
3. 实现心跳机制和断线重连逻辑

## 常见问题

### 1. 连接失败

- 检查服务器地址和端口是否正确
- 确认防火墙设置允许WebSocket连接
- 检查网络连接是否稳定

### 2. 认证失败

- 确认用户ID是否有效
- 检查认证逻辑是否正确实现
- 查看服务器日志获取详细错误信息

### 3. 消息未收到

- 检查房间加入是否成功
- 确认消息发送API调用是否正确
- 查看服务器日志中的消息队列状态

### 4. 心跳超时

- 检查客户端心跳发送频率（默认10秒）
- 确认服务器心跳超时设置（默认60秒）
- 检查网络延迟是否过高

## 性能调优

- 增加`eventlet`工作线程数量提高并发处理能力
- 调整心跳频率和超时时间适应网络环境
- 优化消息队列大小和重试策略

## 安全建议

- 实现更强的认证机制，如JWT或OAuth
- 添加消息加密传输
- 实现IP白名单和连接频率限制
