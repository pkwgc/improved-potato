import logging
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, extract
from sqlalchemy.orm import Session
from database import (
    User, Template, Context, BillingRecord, AIFeedingRecord,
    Industry, Intent, TokenPackage, UserTemplateBinding,
    get_chat_messages, ChatMessage
)

logger = logging.getLogger(__name__)

class StatisticsService:
    """统计服务，提供各类数据统计功能"""
    
    def __init__(self, db: Session):
        """初始化统计服务"""
        self.db = db
    
    def get_dashboard_stats(self):
        """获取管理员仪表盘统计数据"""
        user_count = self.db.query(User).count()
        
        total_tokens = self.db.query(func.sum(BillingRecord.tokens_used)).scalar() or 0
        
        total_duration = self.db.query(func.sum(BillingRecord.duration_seconds)).scalar() or 0
        
        total_conversations = self.db.query(func.count(func.distinct(ChatMessage.context_id))).scalar() or 0
        
        active_users_today = self.db.query(BillingRecord.user_id).distinct().filter(
            BillingRecord.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        active_users_week = self.db.query(BillingRecord.user_id).distinct().filter(
            BillingRecord.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        active_users_month = self.db.query(BillingRecord.user_id).distinct().filter(
            BillingRecord.created_at >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        total_revenue = self.db.query(
            func.sum(TokenPackage.price)
        ).join(
            User, User.token_package == TokenPackage.name
        ).scalar() or 0
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        daily_token_usage = self.db.query(
            func.date(BillingRecord.created_at).label('date'),
            func.sum(BillingRecord.tokens_used).label('tokens')
        ).filter(
            BillingRecord.created_at >= thirty_days_ago
        ).group_by(
            func.date(BillingRecord.created_at)
        ).order_by(
            func.date(BillingRecord.created_at)
        ).all()
        
        token_usage_labels = [str(record.date) for record in daily_token_usage]
        token_usage_data = [int(record.tokens) for record in daily_token_usage]
        
        daily_active_users = self.db.query(
            func.date(BillingRecord.created_at).label('date'),
            func.count(func.distinct(BillingRecord.user_id)).label('users')
        ).filter(
            BillingRecord.created_at >= thirty_days_ago
        ).group_by(
            func.date(BillingRecord.created_at)
        ).order_by(
            func.date(BillingRecord.created_at)
        ).all()
        
        active_users_labels = [str(record.date) for record in daily_active_users]
        active_users_data = [int(record.users) for record in daily_active_users]
        
        template_usage = self.db.query(
            Template.name,
            func.count(Context.id).label('count')
        ).join(
            Context, Context.template_id == Template.id
        ).group_by(
            Template.name
        ).order_by(
            desc('count')
        ).all()
        
        template_usage_labels = [record.name for record in template_usage]
        template_usage_data = [record.count for record in template_usage]
        
        industry_distribution = self.db.query(
            Industry.name,
            func.count(Template.id).label('count')
        ).join(
            Template, Template.industry_id == Industry.id
        ).group_by(
            Industry.name
        ).order_by(
            desc('count')
        ).all()
        
        industry_labels = [record.name for record in industry_distribution]
        industry_data = [record.count for record in industry_distribution]
        
        return {
            "user_count": user_count,
            "total_tokens": total_tokens,
            "total_duration": total_duration,
            "total_conversations": total_conversations,
            "active_users_today": active_users_today,
            "active_users_week": active_users_week,
            "active_users_month": active_users_month,
            "total_revenue": total_revenue,
            "token_usage_labels": token_usage_labels,
            "token_usage_data": token_usage_data,
            "active_users_labels": active_users_labels,
            "active_users_data": active_users_data,
            "template_usage_labels": template_usage_labels,
            "template_usage_data": template_usage_data,
            "industry_labels": industry_labels,
            "industry_data": industry_data
        }
    
    def get_user_stats(self, user_id=None, username=None):
        """获取用户统计数据"""
        if not user_id and not username:
            return None
        
        user = None
        if user_id:
            user = self.db.query(User).filter(User.user_id == user_id).first()
        elif username:
            user = self.db.query(User).filter(User.username == username).first()
        
        if not user:
            return None
        
        total_tokens = self.db.query(
            func.sum(BillingRecord.tokens_used)
        ).filter(
            BillingRecord.user_id == user.id
        ).scalar() or 0
        
        total_duration = self.db.query(
            func.sum(BillingRecord.duration_seconds)
        ).filter(
            BillingRecord.user_id == user.id
        ).scalar() or 0
        
        total_conversations = self.db.query(func.count(func.distinct(ChatMessage.context_id))).join(
            Context, Context.id == ChatMessage.context_id
        ).filter(
            Context.user_id == user.user_id
        ).scalar() or 0
        
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        daily_token_usage = self.db.query(
            func.date(BillingRecord.created_at).label('date'),
            func.sum(BillingRecord.tokens_used).label('tokens')
        ).filter(
            BillingRecord.user_id == user.id,
            BillingRecord.created_at >= seven_days_ago
        ).group_by(
            func.date(BillingRecord.created_at)
        ).order_by(
            func.date(BillingRecord.created_at)
        ).all()
        
        token_usage_labels = [str(record.date) for record in daily_token_usage]
        token_usage_data = [int(record.tokens) for record in daily_token_usage]
        
        daily_conversations = self.db.query(
            func.date(Context.created_at).label('date'),
            func.count(Context.id).label('count')
        ).filter(
            Context.user_id == user.user_id,
            Context.created_at >= seven_days_ago
        ).group_by(
            func.date(Context.created_at)
        ).order_by(
            func.date(Context.created_at)
        ).all()
        
        conversation_labels = [str(record.date) for record in daily_conversations]
        conversation_data = [int(record.count) for record in daily_conversations]
        
        active_days = self.db.query(
            func.count(func.distinct(func.date(BillingRecord.created_at)))
        ).filter(
            BillingRecord.user_id == user.id
        ).scalar() or 0
        
        avg_response_time = self.db.query(
            func.avg(BillingRecord.duration_seconds)
        ).filter(
            BillingRecord.user_id == user.id
        ).scalar() or 0
        
        template_usage = self.db.query(
            Template.name,
            func.count(Context.id).label('count')
        ).join(
            Context, Context.template_id == Template.id
        ).filter(
            Context.user_id == user.id
        ).group_by(
            Template.name
        ).order_by(
            desc('count')
        ).all()
        
        template_usage_labels = [record.name for record in template_usage]
        template_usage_data = [record.count for record in template_usage]
        
        return {
            "user_id": user.user_id,
            "username": user.username,
            "token_balance": user.token_balance,
            "token_limit": user.token_limit,
            "token_package": user.token_package,
            "has_appointment": user.has_appointment,
            "total_tokens": total_tokens,
            "total_duration": total_duration,
            "total_conversations": total_conversations,
            "active_days": active_days,
            "avg_response_time": round(avg_response_time, 2) if avg_response_time else 0,
            "token_usage_labels": token_usage_labels,
            "token_usage_data": token_usage_data,
            "conversation_labels": conversation_labels,
            "conversation_data": conversation_data,
            "template_usage_labels": template_usage_labels,
            "template_usage_data": template_usage_data
        }
    
    def get_billing_stats(self, time_range='month'):
        """获取计费统计数据"""
        filter_date = None
        if time_range == 'today':
            filter_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'yesterday':
            filter_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        elif time_range == 'week':
            filter_date = datetime.utcnow() - timedelta(days=7)
        elif time_range == 'month':
            filter_date = datetime.utcnow() - timedelta(days=30)
        
        query = self.db.query(BillingRecord)
        if filter_date:
            query = query.filter(BillingRecord.created_at >= filter_date)
        
        total_tokens = query.with_entities(
            func.sum(BillingRecord.tokens_used)
        ).scalar() or 0
        
        total_duration = query.with_entities(
            func.sum(BillingRecord.duration_seconds)
        ).scalar() or 0
        
        total_conversations = query.count()
        
        total_users = query.with_entities(
            func.count(func.distinct(BillingRecord.user_id))
        ).scalar() or 0
        
        total_revenue = self.db.query(
            func.sum(TokenPackage.price)
        ).join(
            User, User.token_package == TokenPackage.name
        ).scalar() or 0
        
        if time_range in ['today', 'yesterday']:
            token_usage_trend = query.with_entities(
                extract('hour', BillingRecord.created_at).label('hour'),
                func.sum(BillingRecord.tokens_used).label('tokens')
            ).group_by(
                extract('hour', BillingRecord.created_at)
            ).order_by(
                'hour'
            ).all()
            
            token_usage_labels = [f"{int(record.hour)}:00" for record in token_usage_trend]
        else:
            token_usage_trend = query.with_entities(
                func.date(BillingRecord.created_at).label('date'),
                func.sum(BillingRecord.tokens_used).label('tokens')
            ).group_by(
                func.date(BillingRecord.created_at)
            ).order_by(
                func.date(BillingRecord.created_at)
            ).all()
            
            token_usage_labels = [str(record.date) for record in token_usage_trend]
        
        token_usage_data = [int(record.tokens) for record in token_usage_trend]
        
        if time_range in ['today', 'yesterday']:
            revenue_trend = self.db.query(
                extract('hour', User.updated_at).label('hour'),
                func.sum(TokenPackage.price).label('revenue')
            ).join(
                TokenPackage, User.token_package == TokenPackage.name
            ).filter(
                User.updated_at >= filter_date
            ).group_by(
                extract('hour', User.updated_at)
            ).order_by(
                'hour'
            ).all()
            
            revenue_labels = [f"{int(record.hour)}:00" for record in revenue_trend]
        else:
            revenue_trend = self.db.query(
                func.date(User.updated_at).label('date'),
                func.sum(TokenPackage.price).label('revenue')
            ).join(
                TokenPackage, User.token_package == TokenPackage.name
            ).filter(
                User.updated_at >= filter_date
            ).group_by(
                func.date(User.updated_at)
            ).order_by(
                func.date(User.updated_at)
            ).all()
            
            revenue_labels = [str(record.date) for record in revenue_trend]
        
        revenue_data = [float(record.revenue) for record in revenue_trend]
        
        top_users = self.db.query(
            User.user_id,
            User.username,
            func.sum(BillingRecord.tokens_used).label('total_tokens'),
            func.count(BillingRecord.id).label('conversation_count'),
            func.max(BillingRecord.created_at).label('last_active')
        ).join(
            BillingRecord, BillingRecord.user_id == User.id
        ).group_by(
            User.id
        ).order_by(
            desc('total_tokens')
        ).limit(10).all()
        
        top_users_data = []
        for user in top_users:
            avg_tokens = user.total_tokens / user.conversation_count if user.conversation_count > 0 else 0
            top_users_data.append({
                'user_id': user.user_id,
                'username': user.username,
                'total_tokens': int(user.total_tokens),
                'conversation_count': user.conversation_count,
                'avg_tokens_per_conversation': round(avg_tokens, 2),
                'last_active': user.last_active.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return {
            "total_tokens": total_tokens,
            "total_duration": total_duration,
            "total_conversations": total_conversations,
            "total_users": total_users,
            "total_revenue": total_revenue,
            "token_usage_labels": token_usage_labels,
            "token_usage_data": token_usage_data,
            "revenue_labels": revenue_labels,
            "revenue_data": revenue_data,
            "top_users": top_users_data,
            "time_range": time_range,
            "time_range_text": self._get_time_range_text(time_range)
        }
    
    def get_token_package_stats(self):
        """获取套餐包统计数据"""
        packages = self.db.query(TokenPackage).all()
        
        package_data = []
        total_value = 0
        active_packages_count = 0
        
        for package in packages:
            user_count = self.db.query(User).filter(
                User.token_package == package.name
            ).count()
            
            package_data.append({
                'id': package.id,
                'name': package.name,
                'description': package.description,
                'token_amount': package.token_amount,
                'price': package.price,
                'is_active': package.is_active,
                'user_count': user_count
            })
            
            total_value += package.price
            if package.is_active:
                active_packages_count += 1
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        package_sales = self.db.query(
            func.date(User.updated_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.token_package != None,
            User.updated_at >= thirty_days_ago
        ).group_by(
            func.date(User.updated_at)
        ).order_by(
            func.date(User.updated_at)
        ).all()
        
        package_sales_labels = [str(record.date) for record in package_sales]
        package_sales_data = [record.count for record in package_sales]
        
        package_distribution = self.db.query(
            User.token_package,
            func.count(User.id).label('count')
        ).filter(
            User.token_package != None
        ).group_by(
            User.token_package
        ).order_by(
            desc('count')
        ).all()
        
        package_distribution_labels = [record.token_package for record in package_distribution]
        package_distribution_data = [record.count for record in package_distribution]
        
        return {
            "packages": package_data,
            "total_value": total_value,
            "active_packages_count": active_packages_count,
            "package_sales_labels": package_sales_labels,
            "package_sales_data": package_sales_data,
            "package_distribution_labels": package_distribution_labels,
            "package_distribution_data": package_distribution_data
        }
    
    def get_user_chat_history(self, user_id=None, username=None, page=1, per_page=10, filter_type='all', search=None):
        """获取用户聊天记录"""
        if not user_id and not username:
            return None
        
        user = None
        if user_id:
            user = self.db.query(User).filter(User.user_id == user_id).first()
        elif username:
            user = self.db.query(User).filter(User.username == username).first()
        
        if not user:
            return None
        
        print(f"Found user: id={user.id}, user_id={user.user_id}, username={user.username}")
        
        query = self.db.query(Context).filter(Context.user_id == user.id)
        
        filter_date = None
        if filter_type == 'today':
            filter_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif filter_type == 'week':
            filter_date = datetime.utcnow() - timedelta(days=7)
        elif filter_type == 'month':
            filter_date = datetime.utcnow() - timedelta(days=30)
        
        if filter_date:
            query = query.filter(Context.created_at >= filter_date)
        
        if search:
            query = query.filter(Context.context_data.like(f'%{search}%'))
        
        total_count = query.count()
        total_pages = (total_count + per_page - 1) // per_page
        
        print(f"Found {total_count} contexts for user {user.username}")
        
        query = query.order_by(Context.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        
        contexts = query.all()
        
        conversations = {}
        for context in contexts:
            date_str = context.created_at.strftime('%Y-%m-%d')
            if date_str not in conversations:
                conversations[date_str] = []
            
            messages = []
            try:
                print(f"Processing context id={context.id}, created_at={context.created_at}")
                
                from database import get_chat_messages_from_json
                json_messages = get_chat_messages_from_json(self.db, context.id)
                
                if json_messages:
                    print(f"Found {len(json_messages)} chat messages from JSON for context {context.id}")
                    for msg in json_messages:
                        messages.append({
                            'role': msg.get('role', 'system'),
                            'content': msg.get('content', ''),
                            'time': msg.get('time', context.created_at.strftime('%H:%M:%S')),
                            'tokens': msg.get('tokens', 0)
                        })
                else:
                    from database import get_chat_messages
                    chat_messages = get_chat_messages(self.db, context.id)
                    
                    if chat_messages:
                        print(f"Found {len(chat_messages)} chat messages from database for context {context.id}")
                        for msg in chat_messages:
                            messages.append({
                                'role': msg.role,
                                'content': msg.content,
                                'time': msg.created_at.strftime('%H:%M:%S'),
                                'tokens': msg.tokens_used
                            })
                    elif context.context_data:
                        print(f"No chat messages found, parsing context_data: {context.context_data[:100]}...")
                        try:
                            import json
                            if context.context_data.strip().startswith('[') and context.context_data.strip().endswith(']'):
                                content_list = json.loads(context.context_data)
                                if isinstance(content_list, list):
                                    for msg in content_list:
                                        if isinstance(msg, dict) and 'role' in msg and msg['role'] in ['user', 'assistant']:
                                            tokens = len(msg.get('content', '')) // 4
                                            messages.append({
                                                'role': msg['role'],
                                                'content': msg.get('content', ''),
                                                'time': context.created_at.strftime('%H:%M:%S'),
                                                'tokens': tokens
                                            })
                            else:
                                messages.append({
                                    'role': 'system',
                                    'content': context.context_data[:1000],
                                    'time': context.created_at.strftime('%H:%M:%S'),
                                    'tokens': min(len(context.context_data), 4000) // 4
                                })
                        except json.JSONDecodeError as json_err:
                            print(f"JSON decode error: {str(json_err)}")
                            try:
                                if context.context_data.strip().startswith('[') and context.context_data.strip().endswith(']'):
                                    content_list = eval(context.context_data)
                                    for msg in content_list:
                                        if isinstance(msg, dict) and 'role' in msg and msg['role'] in ['user', 'assistant']:
                                            tokens = len(msg.get('content', '')) // 4
                                            messages.append({
                                                'role': msg['role'],
                                                'content': msg.get('content', ''),
                                                'time': context.created_at.strftime('%H:%M:%S'),
                                                'tokens': tokens
                                            })
                                else:
                                    messages.append({
                                        'role': 'system',
                                        'content': context.context_data[:1000],
                                        'time': context.created_at.strftime('%H:%M:%S'),
                                        'tokens': min(len(context.context_data), 4000) // 4
                                    })
                            except Exception as eval_err:
                                print(f"Eval error: {str(eval_err)}")
                                messages.append({
                                    'role': 'system',
                                    'content': f"无法解析的消息内容 (前1000字符): {context.context_data[:1000]}",
                                    'time': context.created_at.strftime('%H:%M:%S'),
                                    'tokens': min(len(context.context_data), 4000) // 4
                                })
                    else:
                        messages.append({
                            'role': 'system',
                            'content': "空对话记录",
                            'time': context.created_at.strftime('%H:%M:%S'),
                            'tokens': 0
                        })
                
                if not messages:
                    messages.append({
                        'role': 'system',
                        'content': "未找到聊天记录，请检查存储配置",
                        'time': context.created_at.strftime('%H:%M:%S'),
                        'tokens': 0
                    })
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Error processing context {context.id}: {str(e)}\n{error_details}")
                messages.append({
                    'role': 'system',
                    'content': f"加载消息时出错: {str(e)[:200]}",
                    'time': context.created_at.strftime('%H:%M:%S'),
                    'tokens': 0
                })
            
            total_tokens = sum(msg['tokens'] for msg in messages)
            
            template = self.db.query(Template).filter(Template.id == context.template_id).first()
            template_name = template.name if template else "Unknown Template"
            
            conversations[date_str].append({
                'id': context.id,
                'template_name': template_name,
                'time': context.created_at.strftime('%H:%M:%S'),
                'messages': messages,
                'total_tokens': total_tokens
            })
        
        total_conversations = self.db.query(Context).filter(
            Context.user_id == user.id
        ).count()
        
        total_tokens = self.db.query(
            func.sum(BillingRecord.tokens_used)
        ).filter(
            BillingRecord.user_id == user.id
        ).scalar() or 0
        
        avg_response_time = self.db.query(
            func.avg(BillingRecord.duration_seconds)
        ).filter(
            BillingRecord.user_id == user.id
        ).scalar() or 0
        
        active_days = self.db.query(
            func.count(func.distinct(func.date(Context.created_at)))
        ).filter(
            Context.user_id == user.id
        ).scalar() or 0
        
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        conversation_frequency = self.db.query(
            func.date(Context.created_at).label('date'),
            func.count(Context.id).label('count')
        ).filter(
            Context.user_id == user.id,
            Context.created_at >= seven_days_ago
        ).group_by(
            func.date(Context.created_at)
        ).order_by(
            func.date(Context.created_at)
        ).all()
        
        conversation_frequency_labels = [str(record.date) for record in conversation_frequency]
        conversation_frequency_data = [record.count for record in conversation_frequency]
        
        token_usage = self.db.query(
            func.date(BillingRecord.created_at).label('date'),
            func.sum(BillingRecord.tokens_used).label('tokens')
        ).filter(
            BillingRecord.user_id == user.id,
            BillingRecord.created_at >= seven_days_ago
        ).group_by(
            func.date(BillingRecord.created_at)
        ).order_by(
            func.date(BillingRecord.created_at)
        ).all()
        
        token_usage_labels = [str(record.date) for record in token_usage]
        token_usage_data = [int(record.tokens) for record in token_usage]
        
        print(f"Returning data: {len(conversations)} conversation dates, {total_conversations} total conversations")
        
        return {
            "user_info": {
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "token_balance": user.token_balance
            },
            "conversations": conversations,
            "total_conversations": total_conversations,
            "total_tokens": total_tokens,
            "avg_response_time": round(avg_response_time, 2) if avg_response_time else 0,
            "active_days": active_days,
            "page": page,
            "total_pages": total_pages,
            "filter": filter_type,
            "conversation_frequency_labels": conversation_frequency_labels,
            "conversation_frequency_data": conversation_frequency_data,
            "token_usage_labels": token_usage_labels,
            "token_usage_data": token_usage_data
        }
    
    def get_top_users_by_token_usage(self, limit=10):
        """获取按Token使用量排序的前N名用户"""
        top_users = self.db.query(
            User.user_id,
            User.username,
            func.sum(BillingRecord.tokens_used).label('total_tokens'),
            func.count(BillingRecord.id).label('conversation_count'),
            func.max(BillingRecord.created_at).label('last_active')
        ).join(
            BillingRecord, BillingRecord.user_id == User.id
        ).group_by(
            User.id
        ).order_by(
            desc('total_tokens')
        ).limit(limit).all()
        
        top_users_data = []
        for user in top_users:
            avg_tokens = user.total_tokens / user.conversation_count if user.conversation_count > 0 else 0
            top_users_data.append({
                'user_id': user.user_id,
                'username': user.username,
                'total_tokens': int(user.total_tokens),
                'conversation_count': user.conversation_count,
                'avg_tokens_per_conversation': round(avg_tokens, 2),
                'last_active': user.last_active.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return top_users_data
        
    def _get_time_range_text(self, time_range):
        """获取时间范围文本"""
        if time_range == 'today':
            return '今日'
        elif time_range == 'yesterday':
            return '昨日'
        elif time_range == 'week':
            return '本周'
        elif time_range == 'month':
            return '本月'
        else:
            return '全部'
            
    def get_api_calls_count(self, period='today'):
        """获取API调用次数统计"""
        filter_date = None
        if period == 'today':
            filter_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'yesterday':
            filter_date = (datetime.utcnow() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            filter_date = datetime.utcnow() - timedelta(days=7)
        elif period == 'month':
            filter_date = datetime.utcnow() - timedelta(days=30)
        
        query = self.db.query(BillingRecord)
        if filter_date:
            query = query.filter(BillingRecord.created_at >= filter_date)
        
        return query.count()

    def get_token_usage(self, period='month'):
        """获取Token使用量统计"""
        filter_date = None
        if period == 'today':
            filter_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'yesterday':
            filter_date = (datetime.utcnow() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            filter_date = datetime.utcnow() - timedelta(days=7)
        elif period == 'month':
            filter_date = datetime.utcnow() - timedelta(days=30)
        
        query = self.db.query(BillingRecord)
        if filter_date:
            query = query.filter(BillingRecord.created_at >= filter_date)
        
        return query.with_entities(
            func.sum(BillingRecord.tokens_used)
        ).scalar() or 0
