# 管理界面显示修复指南

## 问题描述
AI画像数据已成功生成并存储在 `customer_profiles` 表中，但管理界面 `/admin/customer-profiling` 显示"0个客户"，因为它查询的是 `User` 表而不是 `customer_profiles` 表。

## 修复方案

### 1. 修改 Flask 路由 (app.py 第5925-5951行)

**当前代码:**
```python
@app.route('/admin/customer-profiling')
@admin_required
def admin_customer_profiling():
    db = next(get_db())
    try:
        total_customers = db.query(User).filter(User.is_admin == False).count()
        high_value_customers = db.query(User).filter(
            User.is_admin == False,
            User.value_level == '高价值'
        ).count()
        active_customers = db.query(User).filter(
            User.is_admin == False,
            User.activity_score >= 60
        ).count()
        
        avg_activity = db.query(func.avg(User.activity_score)).filter(
            User.is_admin == False
        ).scalar() or 0
        
        customers = db.query(User).filter(User.is_admin == False).all()
        
        return render_template('admin_customer_profiling.html',
                             total_customers=total_customers,
                             high_value_customers=high_value_customers,
                             active_customers=active_customers,
                             avg_activity_score=round(avg_activity, 1),
                             customers=customers)
    finally:
        db.close()
```

**修复后代码:**
```python
@app.route('/admin/customer-profiling')
@admin_required
def admin_customer_profiling():
    db = next(get_db())
    try:
        # 查询customer_profiles表而不是User表
        total_customers = db.query(CustomerProfile).count()
        high_value_customers = db.query(CustomerProfile).filter(
            CustomerProfile.value_level == '高价值'
        ).count()
        active_customers = db.query(CustomerProfile).filter(
            CustomerProfile.activity_score >= 0.6
        ).count()
        
        avg_activity = db.query(func.avg(CustomerProfile.activity_score)).scalar() or 0
        
        # 联合查询获取完整的客户信息
        customers_data = db.query(
            CustomerProfile,
            WechatContact.nickname,
            WechatContact.wechat_id
        ).join(
            WechatContact, CustomerProfile.contact_id == WechatContact.id
        ).all()
        
        # 转换数据格式以适配模板
        customers = []
        for profile, nickname, wechat_id in customers_data:
            customer_data = {
                'id': profile.id,
                'username': nickname or wechat_id,
                'user_id': wechat_id,
                'value_level': profile.value_level,
                'activity_score': int(profile.activity_score * 100) if profile.activity_score else 0,
                'tags': json.loads(profile.profile_value).get('labels', []) if profile.profile_value else [],
                'created_at': profile.created_at
            }
            customers.append(customer_data)
        
        return render_template('admin_customer_profiling.html',
                             total_customers=total_customers,
                             high_value_customers=high_value_customers,
                             active_customers=active_customers,
                             avg_activity_score=round(avg_activity * 100, 1),
                             customers=customers)
    finally:
        db.close()
```

### 2. 确保导入必要的模型

在 app.py 文件顶部确保导入了所需的模型:
```python
from database import CustomerProfile, WechatContact
```

### 3. 数据库表结构确认

确保 `customer_profiles` 表包含以下字段:
- `contact_id` (关联到 wechat_contacts.id)
- `profile_value` (JSON格式的AI画像数据)
- `value_level` (客户价值等级)
- `activity_score` (活跃度分数，0-1之间的浮点数)

## 验证修复

修复后，访问 `/admin/customer-profiling` 应该能看到:
- 总客户数: 1
- 高价值客户: 1 (如果张小美被分类为高价值)
- 客户列表显示: 张小美的完整画像信息

## 当前AI画像数据示例

系统已生成的AI画像数据:
```json
{
  "summary": "张小美是一个热爱生活、追求品质的年轻女性，对美食、旅行和摄影有浓厚兴趣",
  "labels": ["美食达人", "摄影爱好者", "旅行达人"],
  "category": "高价值客户",
  "hobbies": ["美食探店", "旅行摄影", "数码产品"]
}
```
