# 测试账号信息 / Test Account Information

## 用户账号 / User Accounts

### 普通用户 / Regular User
- **用户名 / Username**: `testuser`
- **密码 / Password**: `testpass123`
- **权限 / Permissions**: 普通用户权限，可访问用户后台
- **访问地址 / Access URL**: http://localhost:5000/user/login

### 管理员用户 / Admin User  
- **用户名 / Username**: `admin`
- **密码 / Password**: `admin123`
- **权限 / Permissions**: 管理员权限，可访问管理员后台
- **访问地址 / Access URL**: http://localhost:5000/admin/login

## 数据库配置 / Database Configuration

### SQLite (本地开发 / Local Development)
```bash
# Windows Command Prompt
set USE_SQLITE=true

# Windows PowerShell  
$env:USE_SQLITE="true"

# Linux/Mac
export USE_SQLITE=true
```

### MySQL (生产环境 / Production)
在 `.env` 文件中配置 MySQL 连接信息：
```
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/database_name
```

## 初始化步骤 / Initialization Steps

1. **安装依赖 / Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **设置环境变量 / Set Environment Variables**
   ```bash
   export USE_SQLITE=true  # 使用SQLite进行本地开发
   ```

3. **创建测试用户 / Create Test Users**
   ```bash
   python create_test_users.py
   ```

4. **启动应用 / Start Application**
   ```bash
   python app.py
   ```

5. **访问系统 / Access System**
   - 用户后台: http://localhost:5000/user/login
   - 管理员后台: http://localhost:5000/admin/login

## 功能验证 / Function Verification

### 用户登录测试 / User Login Test
1. 访问 http://localhost:5000/user/login
2. 输入用户名: `testuser`
3. 输入密码: `testpass123`
4. 点击登录按钮
5. 应该成功跳转到用户仪表板

### 管理员登录测试 / Admin Login Test
1. 访问 http://localhost:5000/admin/login
2. 输入用户名: `admin`
3. 输入密码: `admin123`
4. 点击登录按钮
5. 应该成功跳转到管理员仪表板

## 安全说明 / Security Notes

- 所有密码都使用 werkzeug.security 进行安全哈希存储
- 测试账号仅用于开发和测试环境
- 生产环境请修改默认密码
- 建议在生产环境中使用更强的密码策略

## 故障排除 / Troubleshooting

### 登录失败
- 确认用户名和密码正确
- 检查数据库连接是否正常
- 查看应用日志获取详细错误信息

### 数据库连接问题
- 确认环境变量设置正确
- 检查数据库服务是否运行
- 验证数据库连接字符串格式

### 应用启动失败
- 检查依赖是否完整安装
- 确认Python版本兼容性
- 查看启动日志获取错误详情
