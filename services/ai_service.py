"""
AI Service for WeChat Chatbot System
"""
import logging
from ai_api_client import AIService as BaseAIService, CustomerProfilingService
from proactive_messaging import ProactiveMessagingService
from utils.helpers import extract_reply_and_confidence

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, socketio=None):
        self.base_service = BaseAIService()
        self.customer_profiling_service = CustomerProfilingService()
        self.proactive_messaging_service = ProactiveMessagingService(socketio) if socketio else None
    
    def process_chat_message(self, db, user_id, message, nameuser=None):
        """Process chat message with AI"""
        try:
            return {
                "reply": "AI服务正在处理中...",
                "confidence": 0.5,
                "intent_type": "processing",
                "intent_details": {}
            }
        except Exception as e:
            logger.error(f"AI chat processing error: {e}")
            return {
                "reply": "抱歉，处理您的消息时出现错误。",
                "confidence": 0.0,
                "intent_type": "error",
                "intent_details": {}
            }
    
    def process_initial_sync(self, data):
        """Process initial sync for AI profiling"""
        try:
            return self.customer_profiling_service.process_initial_sync(data)
        except Exception as e:
            logger.error(f"Initial sync processing error: {e}")
            return {"error": "处理初始同步时出现错误"}, 500
    
    def process_profile_update(self, data):
        """Process profile update"""
        try:
            return self.customer_profiling_service.process_profile_update(data)
        except Exception as e:
            logger.error(f"Profile update processing error: {e}")
            return {"error": "处理画像更新时出现错误"}, 500
