# WeChat Payment Android Plugin

这是一个 Android 插件，用于处理来自 H5 页面的微信支付请求。通过自定义 scheme 协议接收支付参数，并调用微信支付 SDK 完成支付流程。

## 功能特性

- 支持通过 scheme 协议 (`wechatpay://` 或 `wxpay://`) 接收 H5 传递的支付参数
- 自动解析微信支付所需的所有参数
- 集成微信支付 SDK，直接调用微信客户端进行支付
- 处理支付结果回调
- 支持将支付结果返回给 H5 页面

## 支持的参数

插件支持以下微信支付参数：

- `prepayId`: 预支付交易会话标识
- `appId`: 应用ID
- `partnerId`: 商户号
- `nonceStr`: 随机字符串
- `sign`: 签名
- `spreadField`: 扩展字段（默认为 "Sign=WXPay"）
- `timestamp`: 时间戳

## 项目结构

```
android_plugin/
├── app/
│   ├── src/main/
│   │   ├── java/com/wechat/payment/
│   │   │   ├── MainActivity.java          # 主活动，处理 scheme 协议
│   │   │   ├── PaymentHandler.java        # 支付处理逻辑
│   │   │   ├── PaymentParams.java         # 支付参数数据类
│   │   │   └── wxapi/
│   │   │       └── WXPayEntryActivity.java # 微信支付回调处理
│   │   ├── AndroidManifest.xml            # 应用配置
│   │   └── res/                           # 资源文件
│   ├── build.gradle                       # 应用构建配置
│   └── proguard-rules.pro                # 代码混淆规则
├── build.gradle                          # 项目构建配置
└── settings.gradle                       # 项目设置
```

## 安装和配置

### 1. 环境要求

- Android Studio 4.0+
- Android SDK API 21+
- Java 8+

### 2. 微信支付 SDK 配置

项目已经配置了微信支付 SDK 依赖：

```gradle
implementation 'com.tencent.mm.opensdk:wechat-sdk-android-without-mta:6.8.0'
```

### 3. 应用签名

微信支付需要应用签名与微信开放平台注册的签名一致。请确保：

1. 在微信开放平台注册应用
2. 获取应用签名并在微信开放平台配置
3. 使用相同的签名打包应用

### 4. 权限配置

应用已配置必要的权限：

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

## 使用方法

### 1. H5 页面调用

在 H5 页面中，使用以下 JavaScript 代码调用 Android 插件：

```javascript
function invokeWeChatPay(paymentParams) {
    const schemeUrl = `wechatpay://pay?prepayId=${paymentParams.prepayId}&appId=${paymentParams.appId}&partnerId=${paymentParams.partnerId}&nonceStr=${paymentParams.nonceStr}&sign=${paymentParams.sign}&spreadField=${paymentParams.spreadField}&timestamp=${paymentParams.timestamp}`;
    window.location.href = schemeUrl;
}

// 示例调用
const params = {
    prepayId: "wx19162432174915e15d5011fb071e330000",
    appId: "wxdf261c3b90ffbc25",
    partnerId: "1236537302",
    nonceStr: "tUQgTXocIAFakmHNEWGGDCtaXIQxKsOc",
    sign: "82B29937ECE7A47F45409BD85B84C951",
    spreadField: "Sign=WXPay",
    timestamp: "1758270368"
};

invokeWeChatPay(params);
```

### 2. 支持的 Scheme 协议

插件支持两种 scheme 协议：

- `wechatpay://pay?参数列表`
- `wxpay://pay?参数列表`

### 3. 参数格式

所有参数通过 URL 查询字符串传递，例如：

```
wechatpay://pay?prepayId=wx123&appId=wx456&partnerId=789&nonceStr=abc&sign=def&spreadField=Sign%3DWXPay&timestamp=1234567890
```

## 测试

### 1. 使用示例 H5 页面

项目包含一个示例 H5 页面 (`h5_example/wechat_payment_demo.html`)，可以用于测试：

1. 在浏览器中打开 `h5_example/wechat_payment_demo.html`
2. 填写或使用预设的支付参数
3. 点击"调用微信支付"按钮
4. 应用将自动启动并处理支付请求

### 2. 应用内测试

应用包含一个测试按钮，可以使用预设的示例数据测试支付流程。

## 支付结果处理

### 1. 支付结果回调

支付完成后，`WXPayEntryActivity` 会接收微信的回调：

- `errCode = 0`: 支付成功
- `errCode = -1`: 支付失败
- `errCode = -2`: 用户取消支付

### 2. 结果返回 H5

插件会尝试通过 scheme 协议将支付结果返回给 H5 页面：

```
wechatpay://result?code=0&message=Payment%20successful
```

H5 页面可以监听这个回调来处理支付结果。

## 注意事项

1. **微信客户端**: 设备必须安装微信客户端，且版本支持微信支付
2. **应用签名**: 应用签名必须与微信开放平台注册的签名一致
3. **网络权限**: 确保应用有网络访问权限
4. **参数验证**: 所有支付参数都会进行验证，无效参数会导致支付失败
5. **错误处理**: 应用包含完整的错误处理和用户提示

## 故障排除

### 常见问题

1. **应用无法启动**: 检查 scheme 协议是否正确配置
2. **微信支付失败**: 检查应用签名和微信开放平台配置
3. **参数解析错误**: 检查 URL 编码和参数格式
4. **微信客户端未安装**: 提示用户安装微信客户端

### 调试日志

应用包含详细的日志输出，可以通过 Android Studio 的 Logcat 查看：

```
Tag: MainActivity - 主活动日志
Tag: PaymentHandler - 支付处理日志
Tag: WXPayEntryActivity - 支付回调日志
```

## 集成到现有系统

如需将此插件集成到现有的微信 AI 系统中，可以：

1. 修改 `order_processing.py` 添加微信支付参数生成逻辑
2. 创建 API 端点接收支付结果回调
3. 更新订单状态处理逻辑

## 许可证

本项目遵循 MIT 许可证。
