# WeChat Payment Android Plugin Integration Guide

## 概述

本指南说明如何将 WeChat Payment Android Plugin 集成到现有的微信 AI 系统中，实现 H5 页面通过 scheme 协议调用 Android 应用进行微信支付。

## 系统架构

```
H5 页面 (Web Browser)
    ↓ scheme://协议调用
Android Plugin (WeChat Payment)
    ↓ 微信支付SDK
微信客户端 (WeChat App)
    ↓ 支付结果回调
Android Plugin
    ↓ HTTP回调/scheme返回
Flask Backend (WeChat AI System)
```

## 集成步骤

### 1. Android Plugin 部署

#### 1.1 构建 Android 应用

```bash
cd android_plugin
./gradlew build
```

#### 1.2 安装到测试设备

```bash
./gradlew installDebug
```

#### 1.3 配置微信支付

1. 在微信开放平台注册应用
2. 获取 AppID 和商户号
3. 配置应用签名
4. 更新 `PaymentHandler.java` 中的配置

### 2. Flask 后端集成

#### 2.1 添加支付路由

在 `app.py` 中添加：

```python
from wechat_payment_integration import register_wechat_payment_routes

# 注册微信支付路由
register_wechat_payment_routes(app)
```

#### 2.2 更新订单处理

`order_processing.py` 已更新，包含：
- `generate_wechat_payment_params()` - 生成支付参数
- 支付方式更新为 "微信支付"

#### 2.3 新增 API 端点

- `POST /api/wechat/payment/prepare` - 准备支付参数
- `POST /api/wechat/payment/callback` - 处理支付回调
- `GET /wechat/payment/demo` - 支付演示页面

### 3. H5 页面集成

#### 3.1 基本调用方式

```javascript
function invokeWeChatPay(paymentParams) {
    const schemeUrl = `wechatpay://pay?prepayId=${paymentParams.prepayId}&appId=${paymentParams.appId}&partnerId=${paymentParams.partnerId}&nonceStr=${paymentParams.nonceStr}&sign=${paymentParams.sign}&spreadField=${paymentParams.spreadField}&timestamp=${paymentParams.timestamp}`;
    window.location.href = schemeUrl;
}
```

#### 3.2 参数获取

```javascript
// 从后端API获取支付参数
fetch('/api/wechat/payment/prepare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        order_number: orderNumber,
        user_id: userId
    })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        invokeWeChatPay(data.payment_params);
    }
});
```

### 4. 支付流程

#### 4.1 完整支付流程

1. **订单创建**: 用户在 AI 聊天中下单
2. **支付准备**: H5 页面调用 `/api/wechat/payment/prepare` 获取支付参数
3. **启动支付**: H5 通过 scheme 协议启动 Android 应用
4. **参数解析**: Android 应用解析 URL 参数
5. **调用微信**: Android 应用调用微信支付 SDK
6. **用户支付**: 用户在微信中完成支付
7. **结果回调**: 微信将结果返回给 Android 应用
8. **状态更新**: Android 应用通过 API 更新订单状态

#### 4.2 支付参数说明

| 参数 | 说明 | 示例值 |
|------|------|--------|
| prepayId | 预支付交易会话标识 | wx19162432174915e15d5011fb071e330000 |
| appId | 应用ID | wxdf261c3b90ffbc25 |
| partnerId | 商户号 | 1236537302 |
| nonceStr | 随机字符串 | tUQgTXocIAFakmHNEWGGDCtaXIQxKsOc |
| sign | 签名 | 82B29937ECE7A47F45409BD85B84C951 |
| spreadField | 扩展字段 | Sign=WXPay |
| timestamp | 时间戳 | 1758270368 |

### 5. 测试验证

#### 5.1 运行测试脚本

```bash
python test_android_plugin.py
```

#### 5.2 手动测试步骤

1. **启动 Flask 应用**:
   ```bash
   cd wechat_ai_system
   python app.py
   ```

2. **访问演示页面**:
   ```
   http://localhost:5000/wechat/payment/demo
   ```

3. **测试支付流程**:
   - 填写订单信息
   - 点击"生成支付参数"
   - 点击"调用微信支付"
   - 验证 Android 应用是否启动

#### 5.3 Android 应用测试

1. **安装应用到设备**
2. **测试 scheme 协议**:
   ```
   adb shell am start -W -a android.intent.action.VIEW -d "wechatpay://pay?prepayId=test&appId=test&partnerId=test&nonceStr=test&sign=test&timestamp=test"
   ```

### 6. 生产环境配置

#### 6.1 微信支付配置

1. **更新配置文件** (`config.py`):
   ```python
   WECHAT_PAY_APP_ID = "your_real_app_id"
   WECHAT_PAY_PARTNER_ID = "your_merchant_id"
   WECHAT_PAY_API_KEY = "your_api_key"
   ```

2. **实现真实的支付参数生成**:
   - 调用微信支付统一下单 API
   - 生成正确的签名
   - 处理支付结果验证

#### 6.2 安全考虑

1. **签名验证**: 确保所有支付参数都经过正确签名
2. **HTTPS**: 生产环境必须使用 HTTPS
3. **参数验证**: 严格验证所有输入参数
4. **日志记录**: 记录所有支付相关操作

### 7. 故障排除

#### 7.1 常见问题

1. **Android 应用无法启动**:
   - 检查 scheme 协议配置
   - 验证 AndroidManifest.xml 设置
   - 确认应用已正确安装

2. **微信支付失败**:
   - 检查应用签名
   - 验证微信开放平台配置
   - 确认微信客户端版本

3. **参数解析错误**:
   - 检查 URL 编码
   - 验证参数格式
   - 查看 Android 应用日志

#### 7.2 调试方法

1. **Android 日志**:
   ```bash
   adb logcat | grep -E "(MainActivity|PaymentHandler|WXPayEntryActivity)"
   ```

2. **Flask 日志**: 查看控制台输出和日志文件

3. **网络抓包**: 使用工具监控 HTTP 请求

### 8. 扩展功能

#### 8.1 支付结果通知

实现支付结果的实时通知：
- WebSocket 连接
- 服务器推送通知
- 邮件/短信通知

#### 8.2 多支付方式

扩展支持其他支付方式：
- 支付宝
- 银联支付
- Apple Pay

#### 8.3 订单管理

增强订单管理功能：
- 订单状态跟踪
- 退款处理
- 对账功能

## 总结

本集成指南提供了完整的 WeChat Payment Android Plugin 集成方案，包括：

- 完整的 Android 项目结构
- Flask 后端集成
- H5 页面调用示例
- 测试验证方法
- 生产环境配置指南

通过遵循本指南，可以成功实现 H5 到 Android 的微信支付集成。
