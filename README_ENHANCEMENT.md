# 朋友圈AI画像分析接口增强说明

## 概述
本次更新为 `/api/initial_sync` 接口新增了 `nickname` 和 `avatar_style` 两个可选字段，用于增强AI画像分析的准确性和个性化程度。

## 新增字段

| 字段名 | 类型 | 必传 | 示例值 | 用途 |
|--------|------|------|--------|------|
| `nickname` | string | 否 | `"后知后觉、"` | 用户昵称，用于识别表达风格与特征 |
| `avatar_style` | string | 否 | `"https://wx.qlogo.cn/mmhead/ver_1/rjNLVztbvVVvzUMKeqEeP5bFKsxeIpTckU9BMNrTGCpAelSiam6icOCmqFtIiaZrrBfFCjnMWP90jA9KvcGYIQPDdMnk661PGcibibtlzldzJg4EmO7M0U5dp3LD3ka9HE72T/132"` | 用户头像地址，用于推测视觉风格 |

## 请求示例

### 包含新字段的请求
```json
{
  "user_id": "guangwolove",
  "user_wxid": "li258304281314",
  "wechat_id": "pk_wgc",
  "nickname": "后知后觉、",
  "avatar_style": "https://wx.qlogo.cn/mmhead/ver_1/rjNLVztbvVVvzUMKeqEeP5bFKsxeIpTckU9BMNrTGCpAelSiam6icOCmqFtIiaZrrBfFCjnMWP90jA9KvcGYIQPDdMnk661PGcibibtlzldzJg4EmO7M0U5dp3LD3ka9HE72T/132",
  "moments": [
    {
      "title": "晒新茶",
      "content": "打了半年的临牌 终于[裂开]",
      "likes": ["friend1", "friend2"],
      "comments": [
        {"user": "friend1", "content": "恭喜恭喜！"},
        {"user": "friend2", "content": "终于等到了"}
      ],
      "user_actions": ["点赞", "评论"]
    }
  ]
}
```

### 不包含新字段的请求（向后兼容）
```json
{
  "user_id": "guangwolove",
  "user_wxid": "li258304281314",
  "wechat_id": "pk_wgc",
  "moments": [
    {
      "title": "晒新茶",
      "content": "打了半年的临牌 终于[裂开]",
      "likes": ["friend1", "friend2"],
      "comments": [
        {"user": "friend1", "content": "恭喜恭喜！"},
        {"user": "friend2", "content": "终于等到了"}
      ],
      "user_actions": ["点赞", "评论"]
    }
  ]
}
```

## AI提示模板增强

新的AI提示模板现在包含用户基本信息：

```
请分析以下微信朋友圈内容，生成用户画像：

用户基本信息：
- 昵称：{nickname}
- 头像风格：{avatar_style}

朋友圈内容：
{moments_content}

请根据用户昵称、头像风格和朋友圈内容综合分析用户特征，并以JSON格式返回：
{
  "summary": "用户画像摘要描述",
  "labels": ["标签1", "标签2", "标签3"],
  "category": "客户分组归类（高价值客户/中价值客户/普通客户/潜力客户）",
  "hobbies": ["兴趣爱好1", "兴趣爱好2", "兴趣爱好3"]
}
```

## 向后兼容性

- 所有现有功能保持100%不变
- 不包含新字段的请求仍能正常工作
- 现有的 `moments_content` 字段和处理逻辑完全不变
- 数据库结构和业务流程保持原样

## 测试

使用提供的测试脚本验证功能：

```bash
python test_nickname_avatar_enhancement.py
```

测试脚本会验证：
1. 向后兼容性 - 不包含新字段的请求
2. 新字段功能 - 包含新字段的请求
3. AI画像分析结果的正确性

## 实现细节

1. **字段提取**: 从请求中安全提取可选的 `nickname` 和 `avatar_style` 字段
2. **AI提示增强**: 将新字段信息集成到AI分析提示中
3. **联系人更新**: 在创建或更新联系人记录时使用新的昵称信息
4. **错误处理**: 当新字段不存在时，使用默认值"未提供"

## 注意事项

- 新字段为可选字段，不会影响现有客户端
- AI分析会根据提供的信息进行更精准的画像生成
- 所有更改都是增量式的，不影响现有数据和功能
