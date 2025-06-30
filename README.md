# WeChat AI Chatbot System - SocketIO Precise Targeting

## 项目概述

本项目实现了微信AI聊天机器人系统的SocketIO精确推送功能，解决了当用户绑定多个微信账号时消息路由不准确的问题。

## 核心功能

### 精确消息路由
- 使用 `wechat_{wechat_id}` 格式的房间名进行消息路由
- 支持一个用户绑定多个微信账号
- 确保消息只发送给指定的微信账号

### 多步认证流程
1. 客户端建立WebSocket连接
2. 发送 `authenticate` 事件进行用户身份验证
3. 发送 `join_wechat_room` 事件加入特定微信账号的消息房间
4. 服务器使用 `wechat_{wechat_id}` 房间进行精确消息推送

### 数据库设计
- `User` 模型：支持绑定多个微信账号
- `WechatContact` 模型：通过 `owner_id` 外键关联用户
- `WechatMessage` 模型：存储消息记录
- `ProactiveMessage` 模型：支持主动消息推送

## 安装和运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动应用
```bash
python app.py
```

### 3. 测试SocketIO连接
```bash
python socketio_test_client.py
```

## API接口

### 发送消息
```
POST /api/send_message
{
    "owner_id": "用户ID",
    "contact_ids": [联系人ID列表],
    "content": "消息内容",
    "wechat_id": "微信账号ID",
    "content_type": "text"
}
```

### 广播消息
```
POST /api/broadcast_message
{
    "sender_id": "发送者ID",
    "wechat_ids": ["微信账号ID列表"],
    "content": "消息内容",
    "content_type": "text"
}
```

### 测试消息
```
POST /api/test_message
{
    "wechat_id": "微信账号ID",
    "content": "测试消息内容"
}
```

## SocketIO事件

### 客户端事件
- `connect`: 建立连接
- `authenticate`: 用户认证
- `join_wechat_room`: 加入微信房间
- `send_direct_message`: 发送直接消息
- `message_ack`: 消息确认
- `heartbeat`: 心跳检测

### 服务器事件
- `connected`: 连接成功
- `auth_success`: 认证成功
- `joined_wechat_room`: 加入房间成功
- `new_message`: 新消息通知
- `message_sent`: 消息发送成功
- `heartbeat_response`: 心跳响应

## 测试场景

### 精确推送测试
1. 用户 `test` 绑定微信账号 `wechat_A` 和 `wechat_B`
2. 发送消息给 `wechat_A`，只有 `wechat_A` 的客户端收到
3. 发送消息给 `wechat_B`，只有 `wechat_B` 的客户端收到
4. 验证消息不会错误地发送到其他微信账号

### 多客户端测试
- 同时运行多个测试客户端
- 验证每个客户端只接收到发送给自己的消息
- 测试心跳机制和断线重连

## 技术特点

- **房间隔离**：每个微信账号有独立的消息房间
- **精确路由**：基于 `wechat_id` 进行消息路由
- **多账号支持**：一个用户可以绑定多个微信账号
- **实时通信**：基于 Flask-SocketIO 的实时消息推送
- **消息确认**：支持消息送达确认机制
- **心跳检测**：保持连接活跃状态

## 项目结构

```
improved-potato/
├── app.py                      # 主应用入口
├── config.py                   # 配置文件
├── database.py                 # 数据库模型
├── requirements.txt            # 依赖包列表
├── api_send_message.py         # 消息发送API
├── proactive_messaging.py      # 主动消息服务
├── socketio_test_client.py     # 测试客户端
├── core/
│   └── app_factory.py          # 应用工厂
└── services/
    └── websocket_service.py    # WebSocket服务
```
