# 微信朋友圈AI画像系统测试指南

## 快速启动

### Windows用户
```cmd
# 方法1：使用启动脚本
start_system.bat

# 方法2：手动启动
set USE_SQLITE=true
pip install -r requirements.txt
python app.py
```

### Linux/Mac用户
```bash
# 方法1：使用启动脚本
chmod +x start_system.sh
./start_system.sh

# 方法2：手动启动
export USE_SQLITE=true
pip install -r requirements.txt
python app.py
```

## 测试AI画像功能

### 使用修复版测试脚本（推荐）
```bash
python test_ai_profiling_workflow_fixed.py
```

### 使用原版测试脚本（已修复认证）
```bash
python test_ai_profiling_workflow.py
```

### 使用环境变量配置认证
```bash
# 设置自定义认证参数
export TEST_APP_ID=wechat_exe_client
export TEST_APP_SECRET=wechat_exe_secret_2024

# 运行测试
python test_ai_profiling_workflow.py
```

## 管理后台访问

启动系统后，访问管理后台：
- URL: http://localhost:5000/admin
- 用户名: admin
- 密码: admin123

### 主要功能页面
- **客户画像管理**: `/admin/customer-profiling` - 查看生成的AI画像
- **AI策略配置**: `/admin/ai_profiling` - 配置AI分析策略
- **联系人管理**: `/admin/contacts` - 管理微信联系人

## 常见问题解决

### 1. 401认证错误
```
错误: {"error": "签名验证失败"}
```

**解决方案:**
- 确保使用正确的HMAC密钥: `wechat_exe_secret_2024`
- 检查时间戳是否在有效范围内（300秒内）
- 验证所有必需的认证头部都已包含

### 2. 数据库文件不存在
```
错误: 数据库文件不存在: wechat_system.db
```

**解决方案:**
- 确保设置了环境变量: `USE_SQLITE=true`
- 重新启动Flask应用，数据库会自动创建
- 检查当前目录权限

### 3. 依赖包安装失败
```
错误: ModuleNotFoundError: No module named 'xxx'
```

**解决方案:**
```bash
# 升级pip
pip install --upgrade pip

# 安装所有依赖
pip install -r requirements.txt

# 单独安装关键包
pip install flask==2.3.3 flask-socketio==5.3.6 sqlalchemy==1.4.46
```

### 4. Flask应用启动失败
```
错误: Address already in use
```

**解决方案:**
```bash
# 查找占用端口的进程
netstat -tulpn | grep :5000

# 杀死占用进程
kill -9 <进程ID>

# 或使用不同端口启动
export FLASK_PORT=5001
python app.py
```

## 测试验证清单

- [ ] 系统启动无错误
- [ ] 管理后台可正常访问
- [ ] AI画像接口返回200状态码
- [ ] 数据库中有画像数据记录
- [ ] 管理界面显示生成的画像
- [ ] 测试脚本执行成功

## API测试示例

### 手动测试API
```bash
# 使用curl测试（需要正确的HMAC签名）
curl -X POST http://localhost:5000/api/initial_sync \
  -H "Content-Type: application/json" \
  -H "X-App-ID: wechat_exe_client" \
  -H "X-Timestamp: $(date +%s)" \
  -H "X-Nonce: $(uuidgen)" \
  -H "X-Signature: <计算的HMAC签名>" \
  -d '{
    "user_id": "test_001",
    "user_wxid": "wxid_test",
    "wechat_id": "wxid_friend",
    "moments": [...]
  }'
```

### 预期响应
```json
{
  "success": true,
  "profile": {
    "summary": "用户画像摘要",
    "labels": ["标签1", "标签2"],
    "category": "高价值客户",
    "hobbies": ["兴趣1", "兴趣2"]
  }
}
```

## 系统架构说明

### 核心组件
- **Flask应用**: 主要的Web服务器和API端点
- **HMAC认证**: 安全的API访问控制
- **AI画像分析**: 基于DeepSeek API的智能分析
- **数据库存储**: SQLite/MySQL双模式支持
- **管理界面**: 完整的后台管理系统

### 数据流程
1. 客户端发送朋友圈数据到 `/api/initial_sync`
2. HMAC认证验证请求合法性
3. AI分析生成结构化画像数据
4. 画像数据存储到 `customer_profiles` 表
5. 管理界面展示分析结果

如果遇到其他问题，请查看系统日志或联系技术支持。
