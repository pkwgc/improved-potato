# Android WeChat Payment Plugin - 测试指南

## 完整测试流程

### 1. 下载和准备

```bash
# 克隆仓库
git clone https://github.com/pkwgc/improved-potato.git
cd improved-potato

# 切换到插件分支
git checkout devin/1737516630-android-wechat-payment-plugin
```

### 2. Android 环境准备

**必需工具：**
- Android Studio (推荐) 或 Android SDK
- Java 8+ 或 Java 11
- Android 设备 (真机，需要安装微信)

**检查环境：**
```bash
# 检查 Java 版本
java -version

# 检查 Android SDK (如果已配置)
adb version
```

### 3. 编译 Android 应用

#### 方法一：使用 Android Studio (推荐)
1. 打开 Android Studio
2. 选择 "Open an existing project"
3. 导航到 `improved-potato/android_plugin` 目录
4. 等待 Gradle 同步完成
5. 点击 "Build" → "Build Bundle(s) / APK(s)" → "Build APK(s)"
6. APK 文件将生成在 `app/build/outputs/apk/debug/` 目录

#### 方法二：使用命令行
```bash
cd android_plugin

# 赋予 gradlew 执行权限 (Linux/Mac)
chmod +x gradlew

# 编译 APK
./gradlew assembleDebug

# Windows 用户使用
# gradlew.bat assembleDebug
```

编译成功后，APK 位置：`app/build/outputs/apk/debug/app-debug.apk`

### 4. 安装到设备

#### 准备设备
1. 在 Android 设备上启用"开发者选项"
2. 启用"USB 调试"
3. 连接设备到电脑
4. 确认设备已连接：`adb devices`

#### 安装应用
```bash
# 方法一：使用 gradle
./gradlew installDebug

# 方法二：使用 adb
adb install app/build/outputs/apk/debug/app-debug.apk

# 如果已安装，强制重新安装
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### 5. 测试 H5 调用

#### 5.1 准备测试页面
```bash
# 启动本地 HTTP 服务器 (Python 3)
cd h5_example
python -m http.server 8000

# 或使用 Python 2
# python -m SimpleHTTPServer 8000
```

#### 5.2 在设备上测试
1. 在手机浏览器中访问：`http://[你的电脑IP]:8000/wechat_payment_demo.html`
2. 填写测试参数（页面已预填示例数据）
3. 点击"调用微信支付"按钮
4. 观察是否成功启动 Android 应用

#### 5.3 使用 ADB 直接测试
```bash
# 测试 scheme 协议调用
adb shell am start -W -a android.intent.action.VIEW -d "wechatpay://pay?prepayId=wx19162432174915e15d5011fb071e330000&appId=wxdf261c3b90ffbc25&partnerId=1236537302&nonceStr=tUQgTXocIAFakmHNEWGGDCtaXIQxKsOc&sign=82B29937ECE7A47F45409BD85B84C951&spreadField=Sign%3DWXPay&timestamp=1758270368"
```

### 6. 查看日志和调试

#### Android 应用日志
```bash
# 查看应用日志
adb logcat | grep -E "(MainActivity|PaymentHandler|WXPayEntryActivity)"

# 或查看所有日志
adb logcat
```

#### 常见问题排查
1. **应用无法启动**：检查 scheme 协议配置和应用安装
2. **参数解析错误**：查看 logcat 输出，检查 URL 编码
3. **"没有安装微信" 错误**：已通过添加 Android 11+ 包可见性配置解决
4. **微信支付失败**：需要配置真实的微信商户信息

### 7. Flask 后端测试 (可选)

如果要测试完整的支付流程：

```bash
cd wechat_ai_system

# 安装依赖 (如果需要)
pip install flask sqlalchemy

# 启动 Flask 应用
python app.py
```

访问：`http://localhost:5000/wechat/payment/demo`

### 8. 预期测试结果

#### 成功指标：
- ✅ Android 应用成功编译和安装
- ✅ H5 页面点击按钮后成功启动 Android 应用
- ✅ Android 应用正确解析支付参数
- ✅ 应用显示支付参数信息
- ✅ 日志中无错误信息

#### 注意事项：
- 🔸 微信支付 SDK 调用需要真实的商户配置
- 🔸 完整支付流程需要微信开放平台应用配置
- 🔸 测试参数仅用于验证 scheme 协议和参数解析

### 9. 故障排除

#### 编译问题
```bash
# 清理并重新编译
./gradlew clean
./gradlew assembleDebug
```

#### 设备连接问题
```bash
# 重启 ADB 服务
adb kill-server
adb start-server
adb devices
```

#### 权限问题
确保应用有必要的权限：
- 网络权限
- 存储权限 (如果需要)

### 10. 下一步

测试成功后，您可以：
1. 配置真实的微信支付商户信息
2. 集成到您的实际应用中
3. 添加更多的错误处理和用户体验优化
4. 部署到生产环境

---

**需要帮助？** 
- 查看详细集成指南：`INTEGRATION_GUIDE.md`
- 运行自动化测试：`python test_android_plugin.py`
- 在 GitHub PR 中留言：https://github.com/pkwgc/improved-potato/pull/7
