import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

AI_API_URL = "http://127.0.0.1:9000"

def get_ai_response(user_id, message, context=""):
    """AI回复接口 - 保持与原函数签名完全相同"""
    try:
        resp = requests.post(f"{AI_API_URL}/ai/response", json={
            "user_id": user_id,
            "message": message,
            "context": context
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["result"]
    except Exception as e:
        logger.error(f"AI回复服务调用失败: {str(e)}")
        return {"error": f"AI服务错误: {str(e)}", "trigger_api": False}

def recognize_intent(message, user_profile=None):
    """意图识别 - 保持与原函数签名完全相同"""
    try:
        resp = requests.post(f"{AI_API_URL}/ai/intent", json={
            "message": message,
            "user_profile": user_profile or {}
        }, timeout=10)
        resp.raise_for_status()
        return resp.json()["intent"]
    except Exception as e:
        logger.error(f"意图识别服务调用失败: {str(e)}")
        return {
            "intent": None,
            "industry": None,
            "api": None,
            "confidence": 0.0,
            "trigger_api": False,
            "slots": {}
        }

def profile_user(user_id):
    """用户画像 - 保持与原函数签名完全相同"""
    try:
        resp = requests.post(f"{AI_API_URL}/ai/profile", json={"user_id": user_id}, timeout=10)
        resp.raise_for_status()
        return resp.json()["profile"]
    except Exception as e:
        logger.error(f"用户画像服务调用失败: {str(e)}")
        return {"tags": []}

class AIServiceClient:
    """AI服务客户端，提供与原AIService相同的接口"""
    
    def __init__(self, api_key: str = "", base_url: str = "", model: str = "", 
                 max_tokens: int = 0, temperature: float = 0.0):
        """保持与原AIService相同的初始化参数"""
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = ChatClient()
    
    def process_chat(self, db, user_id: str, user_message: str, 
                    template_name: str, username: Optional[str] = None,
                    prompt_override: Optional[str] = None) -> Dict[str, Any]:
        """处理聊天请求 - 与原process_chat方法签名完全相同"""
        try:
            response = requests.post(f"{AI_API_URL}/ai/chat", json={
                "user_id": user_id,
                "user_message": user_message,
                "template_name": template_name,
                "username": username,
                "prompt_override": prompt_override
            }, timeout=30)
            response.raise_for_status()
            return response.json()["result"]
        except Exception as e:
            logger.error(f"AI服务调用失败: {str(e)}")
            return {"error": f"AI服务错误: {str(e)}", "trigger_api": False}
    
    def analyze_user_profile(self, user_id: str, content: str, content_type: str = 'moment') -> Dict[str, Any]:
        """分析用户画像 - 从朋友圈内容生成用户画像"""
        try:
            response = requests.post(f"{AI_API_URL}/ai/profile/analyze", json={
                "user_id": user_id,
                "content": content,
                "content_type": content_type
            }, timeout=30)
            response.raise_for_status()
            return response.json()["result"]
        except Exception as e:
            logger.error(f"用户画像分析失败: {str(e)}")
            return {"success": False, "error": f"画像分析失败: {str(e)}"}
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户画像数据"""
        try:
            response = requests.post(f"{AI_API_URL}/ai/profile/update", json={
                "user_id": user_id,
                "profile_data": profile_data
            }, timeout=30)
            response.raise_for_status()
            return response.json()["result"]
        except Exception as e:
            logger.error(f"用户画像更新失败: {str(e)}")
            return {"success": False, "error": f"画像更新失败: {str(e)}"}
    
    def extract_reply_and_confidence(self, content):
        """提取回复和置信度"""
        try:
            response = requests.post(f"{AI_API_URL}/ai/extract", json={
                "content": content
            }, timeout=10)
            response.raise_for_status()
            result = response.json()
            return result.get("reply", content), result.get("confidence", 0.8), result.get("intent_data", {})
        except Exception as e:
            logger.error(f"提取回复和置信度失败: {str(e)}")
            return content, 0.8, {}

class ChatClient:
    """聊天客户端，提供兼容性接口"""
    
    def __init__(self):
        self.chat = ChatCompletions()

class ChatCompletions:
    """聊天完成接口"""
    
    def create(self, model, messages, temperature, max_tokens):
        """创建聊天完成请求"""
        try:
            response = requests.post(f"{AI_API_URL}/ai/chat/completions", json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }, timeout=30)
            response.raise_for_status()
            return ChatResponse(response.json())
        except Exception as e:
            logger.error(f"AI聊天完成调用失败: {str(e)}")
            return ChatResponse({
                "choices": [{"message": {"content": "AI服务暂时不可用"}}],
                "usage": {"total_tokens": 0}
            })

class ChatResponse:
    """聊天响应对象"""
    
    def __init__(self, data):
        self.data = data
    
    def model_dump(self):
        """返回模型数据"""
        return self.data

class CustomerProfilingServiceClient:
    """客户画像服务客户端"""
    
    def analyze_customer_profile(self, db, contact_id: int, message_content: str):
        try:
            response = requests.post(f"{AI_API_URL}/ai/profile/analyze", json={
                "contact_id": contact_id,
                "message_content": message_content
            }, timeout=10)
            response.raise_for_status()
            return response.json()["result"]
        except Exception as e:
            logger.error(f"客户画像分析失败: {str(e)}")
            return False
    
    def update_activity_score(self, db, user_id: str):
        try:
            response = requests.post(f"{AI_API_URL}/ai/profile/activity", json={
                "user_id": user_id
            }, timeout=10)
            response.raise_for_status()
            return response.json()["result"]
        except Exception as e:
            logger.error(f"更新活跃度评分失败: {str(e)}")
            return False
    
    def get_customer_tags(self, db, user_id: str):
        try:
            response = requests.get(f"{AI_API_URL}/ai/profile/tags", params={
                "user_id": user_id
            }, timeout=10)
            response.raise_for_status()
            return response.json()["tags"]
        except Exception as e:
            logger.error(f"获取客户标签失败: {str(e)}")
            return []
    
    def add_customer_tag(self, db, user_id: str, tag: str, source: str = 'AI'):
        try:
            response = requests.post(f"{AI_API_URL}/ai/profile/tags", json={
                "user_id": user_id,
                "tag": tag,
                "source": source
            }, timeout=10)
            response.raise_for_status()
            return response.json()["result"]
        except Exception as e:
            logger.error(f"添加客户标签失败: {str(e)}")
            return False

def update_user_profile_from_message(db, user_id: str, message: str, ai_result: Optional[dict] = None) -> bool:
    """从用户消息中更新用户画像 - 与原函数签名完全相同"""
    try:
        response = requests.post(f"{AI_API_URL}/ai/profile/update", json={
            "user_id": user_id,
            "message": message,
            "ai_result": ai_result
        }, timeout=10)
        response.raise_for_status()
        return response.json()["result"]
    except Exception as e:
        logger.error(f"更新用户画像失败: {str(e)}")
        return False

def analyze_message_intent(message: str):
    """分析消息意图 - 与原函数签名完全相同"""
    try:
        response = requests.post(f"{AI_API_URL}/ai/intent/analyze", json={
            "message": message
        }, timeout=10)
        response.raise_for_status()
        return response.json()["result"]
    except Exception as e:
        logger.error(f"消息意图分析失败: {str(e)}")
        return {
            "primary_intent": None,
            "confidence": 0.0,
            "entities": {},
            "sentiment": "neutral"
        }

def extract_order_info(message: str):
    """从消息中提取订单信息 - 与原函数签名完全相同"""
    try:
        response = requests.post(f"{AI_API_URL}/ai/order/extract", json={
            "message": message
        }, timeout=10)
        response.raise_for_status()
        return response.json()["result"]
    except Exception as e:
        logger.error(f"订单信息提取失败: {str(e)}")
        return {
            "products": [],
            "quantities": [],
            "total_amount": None,
            "delivery_address": None
        }

def extract_user_profile_info(message: str):
    """从消息中提取用户画像信息 - 与原函数签名完全相同"""
    try:
        response = requests.post(f"{AI_API_URL}/ai/profile/extract", json={
            "message": message
        }, timeout=10)
        response.raise_for_status()
        return response.json()["result"]
    except Exception as e:
        logger.error(f"用户画像信息提取失败: {str(e)}")
        return {}

AIService = AIServiceClient
CustomerProfilingService = CustomerProfilingServiceClient
