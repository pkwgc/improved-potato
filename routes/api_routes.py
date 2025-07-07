"""
API Routes for WeChat AI Chatbot System
"""
from flask import Blueprint, request, jsonify
from services.ai_service import AIService
from utils.helpers import handle_proxy_request
from security import rate_limit, request_validation, hmac_signature_required
from database import get_db

api_bp = Blueprint('api', __name__)

@api_bp.route('/proxy', methods=['GET'])
def proxy():
    """图片代理接口"""
    return handle_proxy_request()

@api_bp.route('/initial_sync', methods=['POST'])
@rate_limit()
@hmac_signature_required
@request_validation(required_fields=["user_id", "user_wxid", "wechat_id", "moments"])
def initial_sync():
    """微信朋友圈AI画像&归类接口"""
    from extensions import socketio
    ai_service = AIService(socketio)
    return ai_service.process_initial_sync(request.get_json())

@api_bp.route('/profile/update', methods=['POST'])
@rate_limit()
@hmac_signature_required
@request_validation(required_fields=["user_id", "profile_data"])
def profile_update():
    """画像更新接口"""
    from extensions import socketio
    ai_service = AIService(socketio)
    return ai_service.process_profile_update(request.get_json())

@api_bp.route('/chat', methods=['POST'])
@rate_limit()
@request_validation(required_fields=["user_id", "content"])
def chat():
    """聊天接口"""
    data = request.get_json()
    from extensions import socketio
    ai_service = AIService(socketio)
    db = next(get_db())
    try:
        result = ai_service.process_chat_message(
            db, 
            data.get('user_id'), 
            data.get('content'), 
            data.get('nameuser'),
            data.get('contact_id')
        )
        return jsonify(result)
    finally:
        db.close()
