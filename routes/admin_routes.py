"""
Admin Routes for WeChat AI Chatbot System
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, make_response
from admin_required import admin_required
from database import (
    get_db, User, Template, Industry, Intent, BillingRecord, ChatMessage, 
    TokenPackage, UserTemplateBinding, InventoryUpload, InventoryItem, 
    Order, OrderItem, Sale, WechatContact, WechatMessage, AIStrategy, 
    KeywordFilter, Moment, MomentComment, IntentTracking, CustomerProfile, 
    HumanAgent, ProactiveMessage, OperationLog, UserTrackingConfig
)
from statistics_service import StatisticsService
from decimal_json_encoder import decimal_json_dumps
from datetime import datetime, timedelta
from sqlalchemy import func, desc, or_
import logging
import io
import csv

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            session['admin_logged_in'] = True
            return redirect(url_for('admin.admin_dashboard'))

        return render_template('login.html', error='用户名或密码错误')

    return render_template('login.html')

@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    db = next(get_db())
    try:
        stats_service = StatisticsService(db)
        stats = stats_service.get_dashboard_stats()

        templates = db.query(Template).all()

        return render_template(
            'dashboard.html',
            user_count=stats['user_count'],
            total_tokens=stats['total_tokens'],
            total_duration=stats['total_duration'],
            total_cost=stats['total_revenue'],
            active_users_today=stats['active_users_today'],
            active_users_week=stats['active_users_week'],
            active_users_month=stats['active_users_month'],
            total_conversations=stats['total_conversations'],
            token_usage_labels=stats['token_usage_labels'],
            token_usage_data=stats['token_usage_data'],
            active_users_labels=stats['active_users_labels'],
            active_users_data=stats['active_users_data'],
            template_usage_labels=stats['template_usage_labels'],
            template_usage_data=stats['template_usage_data'],
            industry_labels=stats['industry_labels'],
            industry_data=stats['industry_data'],
            templates=templates,
            now=datetime.now()
        )
    finally:
        db.close()

@admin_bp.route('/users')
@admin_required
def admin_users():
    db = next(get_db())
    try:
        stats_service = StatisticsService(db)
        dashboard_stats = stats_service.get_dashboard_stats()

        page = request.args.get('page', 1, type=int)
        per_page = 10
        search = request.args.get('search', '')
        filter_type = request.args.get('filter', 'all')
        sort_type = request.args.get('sort', 'recent')

        query = db.query(User)

        if search:
            query = query.filter(
                (User.username.like(f'%{search}%')) |
                (User.user_id.like(f'%{search}%'))
            )

        if filter_type == 'active':
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            active_user_ids = db.query(BillingRecord.user_id).distinct().filter(
                BillingRecord.created_at >= seven_days_ago
            ).all()
            active_user_ids = [user_id[0] for user_id in active_user_ids]
            query = query.filter(User.user_id.in_(active_user_ids))
        elif filter_type == 'inactive':
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            active_user_ids = db.query(BillingRecord.user_id).distinct().filter(
                BillingRecord.created_at >= seven_days_ago
            ).all()
            active_user_ids = [user_id[0] for user_id in active_user_ids]
            query = query.filter(~User.user_id.in_(active_user_ids))
        elif filter_type == 'appointment':
            query = query.filter(User.has_appointment == True)

        if sort_type == 'tokens':
            user_tokens = db.query(
                BillingRecord.user_id,
                func.sum(BillingRecord.tokens_used).label('total_tokens')
            ).group_by(BillingRecord.user_id).subquery()

            query = query.outerjoin(
                user_tokens, User.user_id == user_tokens.c.user_id
            ).order_by(desc(user_tokens.c.total_tokens))
        elif sort_type == 'duration':
            user_duration = db.query(
                BillingRecord.user_id,
                func.sum(BillingRecord.duration_seconds).label('total_duration')
            ).group_by(BillingRecord.user_id).subquery()

            query = query.outerjoin(
                user_duration, User.user_id == user_duration.c.user_id
            ).order_by(desc(user_duration.c.total_duration))
        else:
            query = query.order_by(desc(User.created_at))

        total = query.count()
        users = query.offset((page - 1) * per_page).limit(per_page).all()

        user_stats = {}
        for user in users:
            total_tokens = db.query(func.sum(BillingRecord.tokens_used)).filter(
                BillingRecord.user_id == user.user_id
            ).scalar() or 0

            total_duration = db.query(func.sum(BillingRecord.duration_seconds)).filter(
                BillingRecord.user_id == user.user_id
            ).scalar() or 0

            user_stats[user.user_id] = {
                'total_tokens': total_tokens,
                'total_duration': total_duration
            }

        return render_template(
            'admin_users.html',
            users=users,
            user_stats=user_stats,
            page=page,
            per_page=per_page,
            total=total,
            search=search,
            filter_type=filter_type,
            sort_type=sort_type,
            dashboard_stats=dashboard_stats
        )
    finally:
        db.close()

@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin', None)
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.admin_login'))
