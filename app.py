from flask import Flask
from flask_socketio import SocketIO
import logging
from core.app_factory import create_app
from proactive_messaging import ProactiveMessagingService
from database import get_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    app, socketio = create_app()
    
    proactive_service = ProactiveMessagingService(socketio)
    
    @app.route('/test')
    def test_route():
        return {"status": "WeChat AI Chatbot System - SocketIO Precise Targeting", "version": "1.0.0"}
    
    @app.route('/api/test_message', methods=['POST'])
    def test_message():
        """测试消息发送API"""
        from flask import request, jsonify
        try:
            data = request.json
            wechat_id = data.get('wechat_id')
            content = data.get('content', '测试消息')
            
            if not wechat_id:
                return jsonify({"error": "缺少wechat_id参数"}), 400
            
            message_data = {
                "type": "test_message",
                "content": content,
                "content_type": "text",
                "sender": {"id": "system", "name": "系统"},
                "receiver": {"id": wechat_id, "name": wechat_id},
                "timestamp": "2025-06-30T02:20:00Z",
                "require_ack": True
            }
            
            room_name = f"wechat_{wechat_id}"
            socketio.emit('new_message', message_data, room=room_name)
            
            logger.info(f"测试消息已发送到房间: {room_name}")
            
            return jsonify({
                "success": True,
                "message": f"消息已发送到 {room_name}",
                "data": message_data
            })
            
        except Exception as e:
            logger.error(f"发送测试消息失败: {str(e)}")
            return jsonify({"error": "服务器内部错误"}), 500
    
    logger.info("启动WeChat AI Chatbot System - SocketIO Precise Targeting")
    logger.info("访问 http://localhost:5000/test 查看系统状态")
    logger.info("使用 python socketio_test_client.py 测试SocketIO连接")
    
    if __name__ == '__main__':
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, log_output=False)

if __name__ == '__main__':
    main()
