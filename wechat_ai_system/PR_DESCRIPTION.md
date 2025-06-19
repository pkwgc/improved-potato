## WeChat Moments AI Profiling System Implementation

### Overview
This PR implements the `/api/initial_sync` endpoint for WeChat Moments AI profiling, enabling comprehensive user profile analysis based on WeChat moments data. The system analyzes user social media activity to generate detailed customer profiles including behavioral insights, interests, and customer categorization.

### Key Features Implemented

#### 1. `/api/initial_sync` API Endpoint
- **Method**: POST
- **Authentication**: HMAC signature validation
- **Input Parameters**: 
  - `user_id`: Customer account ID
  - `user_wxid`: Customer WeChat ID  
  - `wechat_id`: Current WeChat friend ID
  - `moments`: Array of moments data with detailed structure
- **Response Format**: `{success: true, profile: {summary, labels, category, hobbies}}`

#### 2. AI-Powered User Profiling
- Analyzes WeChat moments content using configurable AI prompts
- Generates comprehensive user profiles with:
  - **Summary**: Behavioral and lifestyle analysis
  - **Labels**: Key personality and interest tags
  - **Category**: Customer segmentation (高价值客户, 普通客户, etc.)
  - **Hobbies**: Extracted interests and activities
- Supports complex moments data including likes, comments, user actions

#### 3. Admin Configuration Interface
- New admin page at `/admin/ai_profiling` for prompt management
- Configurable AI parameters:
  - Custom prompt templates with placeholder support
  - System message configuration
  - Temperature control (0-2)
  - Max tokens limit (100-4000)
- Real-time prompt updates without system restart

### 2. 意向分层与动态统计 ✅
**新增数据模型**：
- `IntentTracking`: 意向跟踪表，记录客户意向变化
- 支持高意向、一般意向、沉默、已成交等分层

**统计与趋势分析**：
- 意向统计页面 (`/admin/intent-statistics`)
- 实时统计各意向层级客户数量
- 趋势变化分析（上升、下降、成交、流失）
- 图表展示意向分布和变化趋势

**配置化分层规则**：
- 在config.py中定义INTENT_LEVELS配置
- 支持动态调整分层标准和关键词

### 3. 智能跟踪主动询问 ✅
**WechatContact模型扩展**：
- `auto_follow_enabled`: 是否启用自动跟踪
- `follow_frequency`: 跟踪频率（daily/weekly/monthly）
- `last_follow_time`: 最后跟踪时间
- `customer_type`: 客户类型
- `follow_disabled_by_user`: 用户申请减少打扰

**ProactiveMessagingService服务**：
- 个性化话术生成，结合客户画像和上下文
- 支持定时发送和立即发送
- 消息状态跟踪和回复检测

**管理界面**：
- 智能跟踪管理页面 (`/admin/proactive-tracking`)
- 话术模板管理
- 主动消息记录和统计

### 4. AI+人工协同导购 ✅
**HumanAgent模型**：
- 人工客服配置，限制只能选择已导入的微信好友
- 支持多选、优先级排序、默认设置

**AI转人工机制**：
- 高意向检测触发人工介入通知
- WebSocket实时通知指定人工微信号
- 完整的转接记录和日志

### 5. 账号微信号绑定数上限 ✅
**配置管理**：
- `DEFAULT_MAX_WECHAT_ACCOUNTS`: 默认绑定数限制
- `GLOBAL_MAX_WECHAT_ACCOUNTS`: 全局最大限制
- 超级管理员可为每账号独立配置

**注册模式调整**：
- `ENABLE_AUTO_REGISTRATION = False`: 禁用自动注册
- 所有新账号必须由admin手动开户

### 6. 角色权限与数据安全 ✅
**权限控制**：
- `admin_required`和`user_required`装饰器
- 数据严格隔离，用户只能访问自己的数据

**操作日志**：
- `OperationLog`模型记录所有关键操作
- 包含操作类型、描述、目标、IP地址等信息

### 7. WebSocket通信兼容性 ✅
**实时通信**：
- 保持现有WebSocket架构
- 新增人工转接通知
- 主动消息推送
- 心跳检测机制

### 8. 系统兼容性与扩展性 ✅
**数据库迁移**：
- `database_migration.py`脚本处理字段和表的添加
- 保证向后兼容，不破坏现有数据

**定时任务**：
- `scheduled_tasks.py`管理定时任务
- 主动消息发送、客户跟进检查、数据清理

### 9. 用户界面增强 ✅
**管理后台新增页面**：
- 客户画像管理 (`admin_customer_profiling.html`)
- 意向统计分析 (`admin_intent_statistics.html`)
- 智能跟踪管理 (`admin_proactive_tracking.html`)

**用户后台新增页面**：
- 客户管理 (`user_customer_management.html`)
- 支持标签编辑、自动跟踪设置、批量操作

## 技术实现要点

### 数据库设计
- 所有新字段都有默认值，确保兼容性
- 使用JSON格式存储灵活的标签数据
- 外键关系保证数据完整性

### 服务架构
- `CustomerProfilingService`: 客户画像分析服务
- `ProactiveMessagingService`: 主动消息服务
- `ScheduledTaskManager`: 定时任务管理

### 前端界面
- 使用Bootstrap 5构建响应式界面
- Chart.js实现数据可视化
- 中文界面，符合用户习惯

### API设计
- RESTful API设计
- 统一的JSON响应格式
- 完善的错误处理

## 安全考虑
- 角色权限严格控制
- 数据隔离防止跨账号访问
- 操作日志记录审计轨迹
- 输入验证和SQL注入防护

## 部署说明
1. 运行数据库迁移脚本：`python database_migration.py`
2. 更新配置文件
3. 重启应用服务
4. 验证新功能正常工作

## 测试验证
- ✅ 数据库迁移脚本测试通过
- ✅ 新增数据模型创建成功
- ✅ 管理后台界面功能完整
- ✅ 用户后台界面功能完整
- ✅ WebSocket通信兼容性保持

## 文件变更统计
- 49个文件变更
- 19,318行新增代码
- 243行删除代码
- 新增核心服务类4个
- 新增数据模型5个
- 新增模板文件30+个

## 兼容性保证
- 保持与现有MySQL数据库完全兼容
- 所有新字段都有默认值
- 不破坏现有业务流程
- 支持SQLite开发环境

本次实现完全满足了用户提出的9大功能增强需求，保持了系统的稳定性和扩展性，为微信AI客户系统提供了强大的客户管理和智能化功能。

---

**Link to Devin run**: https://app.devin.ai/sessions/a74451a9b4634de59f594b18ad89afeb  
**Requested by**: 光畅 (wangguangchang9@gmail.com)
