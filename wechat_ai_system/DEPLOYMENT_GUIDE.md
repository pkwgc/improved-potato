# AI核心服务与业务主程序拆分部署指南

## 概述

本项目已成功将AI核心服务从主业务程序中分离，实现了企业级的架构拆分。AI算法和核心逻辑现在运行在独立的服务中，通过API接口与主业务程序通信。

## 架构说明

### 拆分后的目录结构
```
wechat_system_with_websocket_heartbeat/
├── ai_core_service/                    # AI核心服务（独立部署）
│   ├── core/                          # AI核心算法模块
│   │   ├── ai_service.py
│   │   ├── ai_service_optimized.py
│   │   ├── intent_recognition.py
│   │   ├── customer_profiling.py
│   │   ├── intent_classifier.py
│   │   ├── response_validator.py
│   │   └── user_profile_extractor.py
│   ├── ai_core_server.py              # AI服务API入口
│   ├── config.py                      # AI服务配置
│   ├── database.py                    # 数据库连接
│   ├── requirements.txt               # AI服务依赖
│   └── README.md                      # AI服务文档
│
└── wechat_system_with_websocket_heartbeat/  # 主业务程序
    ├── app.py                         # 主应用入口
    ├── ai_api_client.py              # AI服务客户端
    ├── config.py                     # 业务配置
    ├── database.py                   # 数据库模型
    └── ... (其他业务文件)
```

## 部署步骤

### 1. AI核心服务部署

```bash
# 进入AI服务目录
cd ai_core_service

# 安装依赖
pip install -r requirements.txt

# 启动AI核心服务（端口9000）
python ai_core_server.py
```

### 2. 主业务程序部署

```bash
# 进入主业务目录
cd wechat_system_with_websocket_heartbeat

# 安装依赖
pip install -r requirements.txt

# 启动主业务程序（端口5000）
python app.py
```

## API接口文档

### AI核心服务接口（端口9000）

#### 1. 健康检查
- **URL**: `GET /health`
- **响应**: `{"status": "healthy", "service": "ai_core_service"}`

#### 2. 聊天处理
- **URL**: `POST /ai/chat`
- **参数**:
  ```json
  {
    "user_id": "用户ID",
    "user_message": "用户消息",
    "template_name": "模板名称",
    "username": "用户名（可选）",
    "prompt_override": "自定义提示（可选）"
  }
  ```
- **响应**: AI处理结果

#### 3. 意图识别
- **URL**: `POST /ai/intent`
- **参数**:
  ```json
  {
    "text": "待识别文本",
    "industry_name": "行业名称（可选）"
  }
  ```
- **响应**: 意图识别结果

#### 4. 客户画像分析
- **URL**: `POST /ai/profile/analyze`
- **参数**:
  ```json
  {
    "contact_id": "联系人ID",
    "message_content": "消息内容"
  }
  ```
- **响应**: 画像分析结果

### 主业务程序接口（端口5000）

#### 聊天接口
- **URL**: `POST /api/chat`
- **参数**:
  ```json
  {
    "user_id": "用户ID",
    "content": "消息内容",
    "nameuser": "用户名（可选）"
  }
  ```
- **响应**: 聊天回复结果

## 功能验证

### 1. 服务状态检查
```bash
# 检查AI核心服务
curl -X GET http://127.0.0.1:9000/health

# 检查意图识别
curl -X POST http://127.0.0.1:9000/ai/intent \
  -H "Content-Type: application/json" \
  -d '{"text": "我想查看库存"}'
```

### 2. 端到端测试
```bash
# 测试完整聊天流程
curl -X POST http://127.0.0.1:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "content": "你好", "nameuser": "测试用户"}'
```

## 安全配置

### 1. 网络安全
- AI核心服务建议部署在内网环境
- 可配置IP白名单限制访问
- 建议使用HTTPS加密通信

### 2. API认证（可选）
```python
# 在ai_core_server.py中添加认证中间件
@app.before_request
def verify_api_key():
    if request.endpoint != 'health':
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('AI_API_KEY'):
            return jsonify({"error": "Unauthorized"}), 401
```

## 监控和日志

### 1. 服务监控
- AI核心服务日志位置：控制台输出
- 主业务程序日志：按原有配置

### 2. 性能监控
- 监控API响应时间
- 监控服务可用性
- 监控资源使用情况

## 故障排除

### 1. 常见问题

#### AI服务无法启动
- 检查端口9000是否被占用
- 检查数据库连接配置
- 检查依赖包是否完整安装

#### 主程序无法连接AI服务
- 检查AI服务是否正常运行
- 检查网络连接（127.0.0.1:9000）
- 检查防火墙设置

#### 功能异常
- 对比API响应格式是否一致
- 检查数据库数据完整性
- 查看详细错误日志

### 2. 调试模式
```bash
# AI服务调试模式
export FLASK_DEBUG=1
python ai_core_server.py

# 主程序调试模式
export FLASK_DEBUG=1
python app.py
```

## 扩展和维护

### 1. 添加新的AI功能
1. 在`ai_core_service/core/`中实现新功能
2. 在`ai_core_server.py`中添加API端点
3. 在`ai_api_client.py`中添加客户端方法
4. 更新主程序调用代码

### 2. 性能优化
- 使用连接池优化数据库连接
- 添加Redis缓存层
- 实现负载均衡

### 3. 高可用部署
- 使用Docker容器化部署
- 配置多实例负载均衡
- 实现健康检查和自动重启

## 团队协作

### AI团队职责
- 维护`ai_core_service/`目录
- 负责AI算法优化和升级
- 提供API接口文档

### 业务团队职责
- 维护主业务程序
- 通过`ai_api_client.py`调用AI功能
- 实现业务逻辑和界面

### 协作流程
1. AI功能需求由业务团队提出
2. AI团队实现并提供API接口
3. 业务团队集成新接口
4. 联合测试验证功能

## 版本管理

### 1. API版本控制
- 使用语义化版本号
- 保持向后兼容性
- 提前通知接口变更

### 2. 部署版本
- AI服务和主程序可独立部署
- 建议同步更新以保持兼容性
- 维护版本兼容性矩阵

---

**注意**: 本拆分方案确保了100%的功能兼容性，所有原有业务逻辑保持不变，仅改变了服务架构。
