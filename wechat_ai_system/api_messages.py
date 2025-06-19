from flask import request, jsonify
from database import get_db, WechatMessage
import logging

logger = logging.getLogger(__name__)

def register_api_messages(app):
    @app.route('/api/messages', methods=['GET'])
    def get_messages():
        """获取会话消息列表"""
        try:
            contact_id = request.args.get('contact_id')
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            if not contact_id:
                return jsonify({"error": "缺少contact_id参数"}), 400
                
            db = next(get_db())
            
            messages = db.query(WechatMessage).filter(
                WechatMessage.contact_id == contact_id
            ).order_by(WechatMessage.created_at.desc()).offset(offset).limit(limit).all()
            
            message_list = [
                {
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "content": msg.content,
                    "content_type": msg.content_type,
                    "is_from_ai": msg.is_from_ai,
                    "created_at": msg.created_at.isoformat(),
                    "status": msg.status
                }
                for msg in messages
            ]
            
            return jsonify({"messages": message_list})
        except Exception as e:
            logger.error(f"获取消息列表失败: {str(e)}")
            return jsonify({"error": "服务器内部错误"}), 500
