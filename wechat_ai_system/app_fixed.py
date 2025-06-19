from flask import Flask, request, jsonify, render_template, redirect, url_for, session, Response, make_response, send_file
from openai import OpenAI
import os
import sys
import json
from decimal import Decimal  # Added for Decimal handling
import re
import ast
import requests
import time
import io
import csv
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from database import (
    get_db, create_tables, User, Template, Context, BillingRecord, AIFeedingRecord,
    load_context_from_db, save_context_to_db, get_bound_template_from_db,
    bind_template_to_db, load_user_prompt_from_db, record_billing, record_ai_feeding,
    Industry, Intent, TokenPackage, ChatMessage, UserTemplateBinding, InventoryUpload
)
from intent_recognition import recognize_intent
from security import rate_limit, request_validation
from ai_service import AIService
from user_profile_extractor import update_user_profile_from_message, analyze_message_intent, extract_order_info, extract_user_profile_info
from statistics_service import StatisticsService

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于会话管理

class DecimalJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalJSONEncoder, self).default(obj)

def custom_json_dumps(obj):
    return json.dumps(obj, cls=DecimalJSONEncoder)

@app.route('/user/dashboard')
def user_dashboard():
    """用户仪表盘页面"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))
    
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            return redirect(url_for('user_login'))
        
        binding = db.query(UserTemplateBinding).filter(
            UserTemplateBinding.user_id == user.id
        ).order_by(UserTemplateBinding.updated_at.desc()).first()
        
        current_template = None
        current_template_info = None
        if binding:
            template = db.query(Template).filter(Template.id == binding.template_id).first()
            if template:
                current_template = template.name
                current_template_info = {
                    'id': template.id,
                    'name': template.name,
                    'description': template.description,
                    'industry': template.industry
                }
        
        today_start = datetime.combine(datetime.today(), datetime.min.time())
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
                    'token_amount': package.token_amount,
                    'price': package.price
                }
        
        recent_activities = []
        billing_records = db.query(BillingRecord).filter(
            BillingRecord.user_id == user.id
        ).order_by(BillingRecord.created_at.desc()).limit(5).all()
        
        for record in billing_records:
            recent_activities.append({
                'type': 'billing',
                'description': f"使用了 {record.tokens_used} 个Token",
                'time': record.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        token_usage_data = {
            'labels': [],
            'values': []
        }
        
        for i in range(6, -1, -1):
            day = datetime.today() - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            
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
            token_usage_data=custom_json_dumps(token_usage_data)
        )
    finally:
        db.close()
