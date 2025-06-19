#!/usr/bin/env python3
import os
import sys

print('=== 审批工作流系统测试 ===')
print(f'当前工作目录: {os.getcwd()}')

os.environ['USE_SQLITE'] = 'true'
print(f'USE_SQLITE环境变量: {os.getenv("USE_SQLITE")}')

print('\n1. 测试数据库模型导入...')
try:
    from database import get_db, WechatContact, ProactiveMessage, User
    print('✅ 数据库模型导入成功')
    
    contact_fields = [attr for attr in dir(WechatContact) if not attr.startswith('_')]
    if 'require_approval' in contact_fields:
        print('✅ WechatContact.require_approval字段存在')
    else:
        print('❌ WechatContact.require_approval字段不存在')
    
    message_fields = [attr for attr in dir(ProactiveMessage) if not attr.startswith('_')]
    if 'status' in message_fields:
        print('✅ ProactiveMessage.status字段存在')
    else:
        print('❌ ProactiveMessage.status字段不存在')
        
except Exception as e:
    print(f'❌ 数据库模型导入失败: {e}')
    sys.exit(1)

print('\n2. 测试Flask应用导入...')
try:
    from app import app
    print('✅ Flask应用导入成功')
except Exception as e:
    print(f'❌ Flask应用导入失败: {e}')
    sys.exit(1)

print('\n3. 检查关键路由是否存在...')
try:
    with app.app_context():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(rule.rule)
        
        required_routes = [
            '/user/customer-management',
            '/user/instruction_approval',
            '/user/api/contact/<int:contact_id>/approval-setting'
        ]
        
        for route in required_routes:
            if '<int:contact_id>' in route:
                pattern_found = any('/user/api/contact/' in r and 'approval-setting' in r for r in routes)
                if pattern_found:
                    print(f'✅ 路由存在: {route}')
                else:
                    print(f'❌ 路由不存在: {route}')
            else:
                if route in routes:
                    print(f'✅ 路由存在: {route}')
                else:
                    print(f'❌ 路由不存在: {route}')
                    
except Exception as e:
    print(f'❌ 路由检查失败: {e}')

print('\n4. 检查关键函数是否存在...')
try:
    from app import create_profile_approval_message, push_profile_update
    print('✅ create_profile_approval_message函数存在')
    print('✅ push_profile_update函数存在')
except ImportError as e:
    print(f'❌ 关键函数导入失败: {e}')

print('\n=== 测试完成 ===')
print('审批工作流系统组件检查完毕')
