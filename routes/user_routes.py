"""
User Routes for WeChat AI Chatbot System
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from admin_required import user_required
from database import (
    get_db, User, Template, UserTemplateBinding, ChatMessage, BillingRecord,
    TokenPackage, Industry, InventoryUpload, InventoryItem, Order, OrderItem, Sale
)
from decimal_json_encoder import decimal_json_dumps
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import logging
import hashlib

user_bp = Blueprint('user', __name__)
logger = logging.getLogger(__name__)

@user_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.info(f"用户登录尝试: username={username}")

        if not username or not password:
            return render_template('user_login.html', error='请输入用户名和密码')

        db = next(get_db())
        try:
            user = db.query(User).filter(User.username == username).first()
            logger.info(f"按用户名查找用户: {user is not None}")

            if not user:
                user = db.query(User).filter(User.user_id == username).first()
                logger.info(f"按用户ID查找用户: {user is not None}")

            if user:
                logger.info(f"找到用户: {user.username}, 密码哈希: {user.password[:10] if user.password else 'None'}...")
                
                if user.user_id == password or username == password or user.password == password:
                    logger.info("简单密码验证成功")
                    session['user_id'] = user.user_id
                    session['username'] = user.username
                    session['user_id_str'] = user.user_id
                    session['user_logged_in'] = True
                    return redirect(url_for('user.user_dashboard'))

                if user.password and password:
                    try:
                        password_hash = hashlib.md5(password.encode()).hexdigest()
                        logger.info(f"MD5验证: 输入密码哈希={password_hash[:10]}..., 存储密码哈希={user.password[:10] if user.password else 'None'}...")
                        if user.password == password_hash:
                            logger.info("MD5密码验证成功")
                            session['user_id'] = user.user_id
                            session['username'] = user.username
                            session['user_id_str'] = user.user_id
                            session['user_logged_in'] = True
                            return redirect(url_for('user.user_dashboard'))
                    except Exception as e:
                        logger.error(f"密码验证错误: {str(e)}")
            else:
                logger.info("未找到用户")

            return render_template('user_login.html', error='用户名或密码错误')
        except Exception as e:
            logger.error(f"登录过程中发生错误: {str(e)}")
            return render_template('user_login.html', error='登录系统错误，请稍后重试')
        finally:
            db.close()

    return render_template('user_login.html')

@user_bp.route('/logout')
def user_logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('user_logged_in', None)
    return redirect(url_for('user.user_login'))

@user_bp.route('/dashboard')
@user_required
def user_dashboard():
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('user.user_login'))

        binding = db.query(UserTemplateBinding).filter(
            UserTemplateBinding.user_id == user.id
        ).order_by(UserTemplateBinding.updated_at.desc()).first()

        current_template = "未绑定"
        current_template_info = None

        if binding:
            template = db.query(Template).filter(Template.id == binding.template_id).first()
            if template:
                current_template = template.name

                industry_name = None
                if template.industry_id:
                    industry = db.query(Industry).filter(Industry.id == template.industry_id).first()
                    if industry:
                        industry_name = industry.name

                current_template_info = {
                    'name': template.name,
                    'industry_name': industry_name,
                    'description': f"适用于{industry_name}行业的专业AI对话模板，帮助您更好地与客户互动" if industry_name else "通用场景AI对话模板，适用于各种客户互动场景"
                }

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_chat_count = db.query(ChatMessage).filter(
            ChatMessage.user_id == user.id,
            ChatMessage.created_at >= today_start
        ).count()

        recent_messages = []
        chat_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user.id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()

        for msg in reversed(chat_messages):
            recent_messages.append({
                'role': msg.role,
                'content': msg.content
            })

        package_info = None
        if user.token_package:
            package = db.query(TokenPackage).filter(TokenPackage.name == user.token_package).first()
            if package:
                package_info = {
                    'name': package.name,
                    'description': package.description,
                    'token_amount': package.token_amount
                }

        recent_activities = []

        billing_records = db.query(BillingRecord).filter(
            BillingRecord.user_id == user.id
        ).order_by(BillingRecord.created_at.desc()).limit(5).all()

        for record in billing_records:
            recent_activities.append({
                'icon': 'bi-chat-dots',
                'description': f'使用了 {record.template_name} 模板',
                'timestamp': record.created_at.strftime('%Y-%m-%d %H:%M'),
                'tokens': record.tokens_used
            })

        token_usage_data = {
            'labels': [],
            'values': []
        }

        for i in range(7):
            day = datetime.utcnow() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

            daily_tokens = db.query(func.sum(BillingRecord.tokens_used)).filter(
                BillingRecord.user_id == user.id,
                BillingRecord.created_at >= day_start,
                BillingRecord.created_at <= day_end
            ).scalar() or 0

            token_usage_data['labels'].insert(0, day.strftime('%m-%d'))
            token_usage_data['values'].insert(0, daily_tokens)

        return render_template(
            'user_dashboard.html',
            user=user,
            current_template=current_template,
            current_template_info=current_template_info,
            today_chat_count=today_chat_count,
            recent_messages=recent_messages,
            package_info=package_info,
            recent_activities=recent_activities,
            token_usage_data=decimal_json_dumps(token_usage_data),
            token_usage_labels=decimal_json_dumps(token_usage_data['labels']),
            token_usage_values=decimal_json_dumps(token_usage_data['values'])
        )
    finally:
        db.close()
