import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database import (
    User, WechatContact, ProactiveMessage, Template, get_db
)
from config import AI_RESPONSE_FORMAT, CUSTOM_PLACEHOLDERS, fill_placeholders

logger = logging.getLogger(__name__)

class ProactiveMessagingService:
    """主动消息服务"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
    
    def generate_personalized_message(self, db: Session, contact_id: int, message_type: str) -> str:
        """生成个性化消息"""
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
        """安排主动消息"""
        try:
            contact = db.query(WechatContact).filter(WechatContact.id == contact_id).first()
            if not contact or contact.follow_disabled_by_user:
                return False
            
            if not manual_trigger and not contact.auto_follow_enabled:
                return False
            
            content = self.generate_personalized_message(db, contact_id, message_type)
            
            if not scheduled_time:
                scheduled_time = datetime.now() + timedelta(days=1)
            
            proactive_msg = ProactiveMessage(
                contact_id=contact_id,
                message_type=message_type,
                content=content,
                scheduled_time=scheduled_time,
                status='pending'
            )
            
            db.add(proactive_msg)
            db.commit()
            
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
