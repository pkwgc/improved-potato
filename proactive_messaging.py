import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database import (
    User, WechatContact, ProactiveMessage, Template, 
    IntentTracking, CustomerProfile, WechatMessage, UserTrackingConfig, OperationLog, get_db
)
from ai_service_final import AIService
from config import AI_RESPONSE_FORMAT, CUSTOM_PLACEHOLDERS, fill_placeholders

logger = logging.getLogger(__name__)

class ProactiveMessagingService:
    """主动消息服务"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.ai_service = AIService()  # 初始化AI服务
    
    def generate_personalized_message(self, db: Session, contact_id: int, message_type: str) -> str:
        """生成个性化消息，为手动跟踪提供简单预设消息避免AI调用超时"""
        try:
            contact = db.query(WechatContact).filter(WechatContact.id == contact_id).first()
            if not contact:
                return "您好，有什么可以帮助您的吗？"
            
            nickname = contact.nickname or contact.wechat_id
            message_templates = {
                "关怀": f"您好 {nickname}，最近怎么样？有什么需要帮助的吗？",
                "问候": f"您好 {nickname}，希望您一切都好！",
                "跟进": f"您好 {nickname}，想了解一下您最近的情况。",
                "提醒": f"您好 {nickname}，有一些重要信息想与您分享。"
            }
            
            if message_type in message_templates:
                return message_templates[message_type]
            else:
                return f"您好 {nickname}，有什么可以帮助您的吗？"
                
        except Exception as e:
            logger.error(f"生成个性化消息失败: {str(e)}")
            return "您好，有什么可以帮助您的吗？"
    
    def schedule_proactive_message(self, db: Session, contact_id: int, message_type: str, 
                                 scheduled_time: Optional[datetime] = None, manual_trigger: bool = False):
        """安排主动消息 - 使用用户配置的跟踪策略"""
        try:
            contact = db.query(WechatContact).filter(WechatContact.id == contact_id).first()
            if not contact or contact.follow_disabled_by_user:
                return False
            
            if not manual_trigger and not contact.auto_follow_enabled:
                return False
            
            user_config = db.query(UserTrackingConfig).filter(
                UserTrackingConfig.user_id == contact.owner_id,
                UserTrackingConfig.customer_type == contact.customer_type
            ).first()
            
            if not user_config:
                logger.info(f"联系人 {contact_id} 的跟踪配置不存在，自动创建默认配置")
                
                default_configs = {
                    '潜在客户': {
                        'tracking_cycle_days': 90,
                        'tracking_periods': 3,
                        'period_duration_days': 30,
                        'max_contacts_per_period': 2,
                        'contact_interval_days': 7,
                        'silence_threshold_periods': 3
                    },
                    '高意向客户': {
                        'tracking_cycle_days': 60,
                        'tracking_periods': 2,
                        'period_duration_days': 30,
                        'max_contacts_per_period': 3,
                        'contact_interval_days': 5,
                        'silence_threshold_periods': 2
                    },
                    '成交客户': {
                        'tracking_cycle_days': 180,
                        'tracking_periods': 6,
                        'period_duration_days': 30,
                        'max_contacts_per_period': 1,
                        'contact_interval_days': 14,
                        'silence_threshold_periods': 6
                    }
                }
                
                if contact.customer_type in default_configs:
                    try:
                        config_data = default_configs[contact.customer_type]
                        user_config = UserTrackingConfig(
                            user_id=contact.owner_id,
                            customer_type=contact.customer_type,
                            auto_tracking_enabled=True,
                            **config_data
                        )
                        db.add(user_config)
                        db.commit()
                        
                        log_entry = OperationLog(
                            user_id=contact.owner_id,
                            operation_type='自动创建跟踪配置',
                            operation_desc=f'为联系人 {contact.nickname or contact.wechat_id} 自动创建 {contact.customer_type} 跟踪配置',
                            target_type='UserTrackingConfig',
                            target_id=str(user_config.id)
                        )
                        db.add(log_entry)
                        db.commit()
                        
                        logger.info(f"已为用户 {contact.owner_id} 创建 {contact.customer_type} 的默认跟踪配置")
                        
                    except Exception as e:
                        logger.error(f"创建默认跟踪配置失败: {str(e)}")
                        db.rollback()
                        return False
                else:
                    logger.error(f"未知的客户类型: {contact.customer_type}")
                    return False
                
            if not manual_trigger and not user_config.auto_tracking_enabled:
                logger.info(f"联系人 {contact_id} 的自动跟踪配置未启用")
                return False
            
            if not manual_trigger and not self._should_send_message_by_user_config(contact, user_config):
                return False
            
            content = self.generate_personalized_message(db, contact_id, message_type)
            
            if not scheduled_time:
                scheduled_time = datetime.now() + timedelta(days=user_config.contact_interval_days)
            
            proactive_msg = ProactiveMessage(
                contact_id=contact_id,
                message_type=message_type,
                content=content,
                scheduled_time=scheduled_time,
                status='pending'
            )
            
            db.add(proactive_msg)
            db.commit()
            
            self._update_contact_tracking_status(db, contact, user_config)
            
            logger.info(f"已安排主动消息: 联系人ID={contact_id}, 类型={message_type}, 时间={scheduled_time}")
            return True
            
        except Exception as e:
            logger.error(f"安排主动消息失败: {str(e)}")
            return False
    
    def send_pending_messages(self, db: Session):
        """发送待发送的主动消息"""
        try:
            pending_messages = db.query(ProactiveMessage).filter(
                ProactiveMessage.status == 'pending',
                ProactiveMessage.scheduled_time <= datetime.now()
            ).all()
            
            for msg in pending_messages:
                success = self._send_message_via_websocket(msg)
                if success:
                    msg.status = 'sent'
                    msg.sent_time = datetime.now()
                    
                    contact = db.query(WechatContact).filter(WechatContact.id == msg.contact_id).first()
                    if contact:
                        contact.last_follow_time = datetime.now()
                else:
                    msg.status = 'failed'
            
            db.commit()
            logger.info(f"处理了 {len(pending_messages)} 条待发送消息")
            
        except Exception as e:
            logger.error(f"发送待发送消息失败: {str(e)}")
    
    def _should_send_message_by_user_config(self, contact: WechatContact, user_config: UserTrackingConfig) -> bool:
        """根据用户配置判断是否应该发送消息"""
        try:
            if contact.is_silenced:
                return False
            
            if not contact.tracking_start_date:
                contact.tracking_start_date = datetime.now()
                contact.current_period = 1
                contact.period_contact_count = 0
                return True
            
            days_since_start = (datetime.now() - contact.tracking_start_date).days
            expected_period = min(
                (days_since_start // user_config.period_duration_days) + 1,
                user_config.tracking_periods
            )
            
            if days_since_start > user_config.tracking_cycle_days:
                return False
            
            if expected_period > contact.current_period:
                contact.current_period = expected_period
                contact.period_contact_count = 0
            
            if contact.period_contact_count >= user_config.max_contacts_per_period:
                return False
            
            if contact.last_follow_time:
                days_since_last = (datetime.now() - contact.last_follow_time).days
                if days_since_last < user_config.contact_interval_days:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"判断是否发送消息失败: {str(e)}")
            return False

    def _update_contact_tracking_status(self, db: Session, contact: WechatContact, user_config: UserTrackingConfig):
        """更新联系人跟踪状态"""
        try:
            contact.period_contact_count += 1
            contact.last_follow_time = datetime.now()
            db.commit()
            
        except Exception as e:
            logger.error(f"更新联系人跟踪状态失败: {str(e)}")

    def check_and_update_silence_status(self, db: Session):
        """检查并更新沉默状态"""
        try:
            contacts = db.query(WechatContact).filter(
                WechatContact.auto_follow_enabled == True,
                WechatContact.follow_disabled_by_user == False,
                WechatContact.is_silenced == False
            ).all()
            
            for contact in contacts:
                user_config = db.query(UserTrackingConfig).filter(
                    UserTrackingConfig.user_id == contact.owner_id,
                    UserTrackingConfig.customer_type == contact.customer_type
                ).first()
                
                if not user_config:
                    continue
                
                recent_messages = db.query(ProactiveMessage).filter(
                    ProactiveMessage.contact_id == contact.id,
                    ProactiveMessage.status == 'sent'
                ).order_by(ProactiveMessage.sent_time.desc()).limit(user_config.silence_threshold_periods).all()
                
                if len(recent_messages) >= user_config.silence_threshold_periods:
                    all_no_response = all(not msg.response_received for msg in recent_messages)
                    if all_no_response: 
                        contact.is_silenced = True
                        contact.silence_period_count = user_config.silence_threshold_periods
                        
                        log_entry = OperationLog(
                            user_id=contact.owner_id,
                            operation_type='沉默状态更新',
                            operation_desc=f'联系人 {contact.nickname or contact.wechat_id} 被标记为沉默',
                            target_type='WechatContact',
                            target_id=str(contact.id)
                        )
                        db.add(log_entry)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"检查沉默状态失败: {str(e)}")
    
    def _send_message_via_websocket(self, message: ProactiveMessage) -> bool:
        """通过WebSocket发送消息"""
        try:
            if not self.socketio:
                return False
            
            contact = message.contact
            if not contact:
                return False
            
            message_data = {
                "type": "proactive_message",
                "content": message.content,
                "content_type": "text",
                "sender": {"id": "system", "name": "系统"},
                "receiver": {"id": contact.wechat_id, "name": contact.nickname or contact.remark},
                "timestamp": datetime.now().isoformat(),
                "require_ack": True
            }
            
            room_name = f"wechat_{contact.wechat_id}"
            self.socketio.emit('new_message', message_data, room=room_name)
            
            logger.info(f"已通过WebSocket发送主动消息: 房间={room_name}")
            return True
            
        except Exception as e:
            logger.error(f"通过WebSocket发送消息失败: {str(e)}")
            return False
    
    def check_and_schedule_follow_ups(self, db: Session):
        """检查并安排跟进消息"""
        try:
            contacts = db.query(WechatContact).filter(
                WechatContact.auto_follow_enabled == True,
                WechatContact.follow_disabled_by_user == False
            ).all()
            
            for contact in contacts:
                if self._should_send_follow_up(contact):
                    message_type = self._determine_message_type(db, contact)
                    self.schedule_proactive_message(db, contact.id, message_type)
            
        except Exception as e:
            logger.error(f"检查跟进消息失败: {str(e)}")
    
    def _should_send_follow_up(self, contact: WechatContact) -> bool:
        """判断是否应该发送跟进消息"""
        if not contact.last_follow_time:
            return True
        
        now = datetime.now()
        time_diff = now - contact.last_follow_time
        
        if contact.follow_frequency == "daily" and time_diff.days >= 1:
            return True
        elif contact.follow_frequency == "weekly" and time_diff.days >= 7:
            return True
        elif contact.follow_frequency == "monthly" and time_diff.days >= 30:
            return True
        
        return False
    
    def _determine_message_type(self, db: Session, contact: WechatContact) -> str:
        """确定消息类型"""
        if contact.customer_type == "成交客户":
            return "复购提醒"
        elif contact.customer_type == "高意向客户":
            return "营销"
        else:
            return "关怀"
    
    def _get_bound_template(self, db: Session, user_id: str) -> Optional[str]:
        """获取用户绑定的提示词模板"""
        try:
            from database import get_bound_template_from_db
            return get_bound_template_from_db(db, user_id) or "default"
        except Exception as e:
            logger.error(f"获取绑定模板失败: {str(e)}")
            return "default"
    
    def _get_global_placeholders(self, db: Session) -> Dict[str, str]:
        """获取全局占位符配置"""
        placeholders = {}
        
        try:
            custom_placeholders = json.loads(CUSTOM_PLACEHOLDERS)
            for placeholder in custom_placeholders:
                name = placeholder.get("name", "")
                default = placeholder.get("default", "")
                if name:
                    placeholders[f"{{{name}}}"] = default
        except json.JSONDecodeError:
            logger.error("解析自定义占位符失败")
        
        return placeholders
    
    def _get_recent_moments(self, db: Session, contact: WechatContact) -> str:
        """获取联系人最近朋友圈内容"""
        try:
            recent_moments = db.query(WechatMessage).filter(
                WechatMessage.sender_id == contact.wechat_id,
                WechatMessage.content_type == "moments"
            ).order_by(WechatMessage.timestamp.desc()).limit(5).all()
            
            if recent_moments:
                moments_content = []
                for moment in recent_moments:
                    content = moment.content[:100] if moment.content else ""
                    if content:
                        moments_content.append(content)
                return "\n".join(moments_content)
            else:
                return "暂无朋友圈动态"
        except Exception as e:
            logger.error(f"获取朋友圈内容失败: {str(e)}")
            return "暂无朋友圈动态"
    
    def _get_customer_profile(self, db: Session, contact: WechatContact) -> str:
        """获取客户画像信息"""
        try:
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.contact_id == contact.id,
                CustomerProfile.profile_type == "综合画像"
            ).order_by(CustomerProfile.updated_at.desc()).first()
            
            if profile and profile.profile_value:
                try:
                    profile_data = json.loads(profile.profile_value)
                    summary = profile_data.get('summary', '无画像信息')
                    labels = profile_data.get('labels', [])
                    category = profile_data.get('category', '普通客户')
                    
                    profile_text = f"画像摘要：{summary}\n"
                    if labels:
                        profile_text += f"标签：{', '.join(labels)}\n"
                    profile_text += f"分类：{category}"
                    
                    return profile_text
                except json.JSONDecodeError:
                    return "画像数据解析失败"
            else:
                return "暂无画像信息"
        except Exception as e:
            logger.error(f"获取客户画像失败: {str(e)}")
            return "暂无画像信息"
    
    def _get_intent_history(self, db: Session, contact: WechatContact) -> str:
        """获取意图历史"""
        try:
            recent_intents = db.query(IntentTracking).filter(
                IntentTracking.contact_id == contact.id
            ).order_by(IntentTracking.detected_at.desc()).limit(3).all()
            
            if recent_intents:
                intent_list = []
                for intent in recent_intents:
                    intent_text = f"{intent.intent_type}({intent.confidence:.2f})"
                    intent_list.append(intent_text)
                return "最近意图：" + ", ".join(intent_list)
            else:
                return "暂无意图记录"
        except Exception as e:
            logger.error(f"获取意图历史失败: {str(e)}")
            return "暂无意图记录"
    
    def _build_message_prompt(self, db: Session, contact: WechatContact, message_type: str) -> str:
        """构建AI消息生成提示词，集成全局占位符"""
        
        global_placeholders = self._get_global_placeholders(db)
        
        prompt = f"请为联系人生成一条{message_type}类型的个性化消息。\n\n"
        
        placeholder_data = {
            "customer_name": contact.nickname or contact.remark or contact.wechat_id,
            "moments_content": self._get_recent_moments(db, contact),
            "customer_profile": self._get_customer_profile(db, contact),
            "intent_history": self._get_intent_history(db, contact)
        }
        
        placeholder_data.update(global_placeholders)
        
        prompt += f"联系人信息：\n"
        prompt += f"- 姓名：{placeholder_data['customer_name']}\n"
        prompt += f"- {placeholder_data['customer_profile']}\n"
        prompt += f"- {placeholder_data['intent_history']}\n\n"
        
        prompt += f"最近朋友圈动态：\n{placeholder_data['moments_content']}\n\n"
        
        prompt += f"请根据以上信息生成一条自然、个性化的{message_type}消息，体现对客户的了解和关怀。"
        
        prompt = fill_placeholders(prompt, placeholder_data)
        
        return prompt
    
    def _extract_reply_from_response(self, ai_response: Dict[str, Any]) -> str:
        """从AI响应中提取回复内容"""
        try:
            if isinstance(ai_response, dict):
                if "raw_content" in ai_response:
                    try:
                        response_data = json.loads(ai_response["raw_content"])
                        return response_data.get("reply", "您好，有什么可以帮助您的吗？")
                    except json.JSONDecodeError:
                        pass
                
                if "reply" in ai_response:
                    return ai_response["reply"]
                
                if "intent_type" in ai_response and "reply" in ai_response:
                    return ai_response["reply"]
            
            if isinstance(ai_response, str):
                try:
                    response_data = json.loads(ai_response)
                    return response_data.get("reply", "您好，有什么可以帮助您的吗？")
                except json.JSONDecodeError:
                    return ai_response
            
            return "您好，有什么可以帮助您的吗？"
            
        except Exception as e:
            logger.error(f"解析AI响应失败: {str(e)}")
            return "您好，有什么可以帮助您的吗？"
