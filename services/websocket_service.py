"""
WebSocket Service for real-time communication
"""
import json
import logging
from datetime import datetime
from flask_socketio import emit, join_room, leave_room
from database import get_db, WechatContact

logger = logging.getLogger(__name__)

def register_socketio_handlers(socketio):
    """Register all SocketIO event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info("Client connected")
        emit('connected', {'status': 'connected'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info("Client disconnected")
    
    @socketio.on('authenticate')
    def handle_authenticate(data):
        """Handle user authentication"""
        user_id = data.get('user_id')
        if not user_id:
            emit('error', {'message': 'Missing user_id'})
            return
        
        emit('auth_success', {'user_id': user_id, 'status': 'authenticated'})
        logger.info(f"User {user_id} authenticated")
    
    @socketio.on('join_wechat_room')
    def handle_join_room(data):
        """Handle joining WeChat room"""
        user_id = data.get('user_id')
        wechat_id = data.get('wechat_id')
        
        if not user_id or not wechat_id:
            emit('error', {'message': 'Missing required parameters'})
            return
        
        room = f'wechat_{wechat_id}'
        join_room(room)
        
        emit('joined_wechat_room', {'wechat_id': wechat_id, 'room_id': room})
        logger.info(f"User {user_id} joined room {room}")
    
    @socketio.on('send_direct_message')
    def handle_send_message(data):
        """Handle sending direct message"""
        user_id = data.get('user_id')
        wechat_id = data.get('wechat_id')
        contact_id = data.get('contact_id')
        content = data.get('content')
        content_type = data.get('content_type', 'text')
        
        if not all([user_id, wechat_id, contact_id, content]):
            emit('error', {'message': 'Missing required parameters'})
            return
        
        message_id = f'msg_{int(datetime.now().timestamp() * 1000)}'
        
        emit('message_sent', {'status': 'sent', 'message_id': message_id})
        
        room = f'wechat_{wechat_id}'
        new_message = {
            'id': message_id,
            'type': 'message',
            'content': content,
            'content_type': content_type,
            'sender': {'id': user_id, 'name': user_id},
            'receiver': {'id': contact_id, 'name': contact_id, 'is_group': False},
            'timestamp': datetime.now().isoformat(),
            'require_ack': True
        }
        
        socketio.emit('new_message', new_message, room=room)
        logger.info(f"Message sent to room {room}")
        
        _update_contact_activity(contact_id)
    
    @socketio.on('message_ack')
    def handle_message_ack(data):
        """Handle message acknowledgment"""
        message_id = data.get('message_id')
        if message_id:
            emit('ack_received', {'message_id': message_id, 'status': 'acknowledged'})
            logger.info(f"Message {message_id} acknowledged")
    
    @socketio.on('heartbeat')
    def handle_heartbeat(data):
        """Handle heartbeat"""
        emit('heartbeat_response', {'status': 'alive', 'timestamp': datetime.now().timestamp()})

def _update_contact_activity(contact_id):
    """Update contact last activity time"""
    try:
        db = next(get_db())
        
        try:
            contact_id_int = int(contact_id)
            contact = db.query(WechatContact).filter(
                WechatContact.id == contact_id_int
            ).first()
        except (ValueError, TypeError):
            contact = db.query(WechatContact).filter(
                WechatContact.wechat_id == contact_id
            ).first()
        
        if contact:
            contact.last_active_at = datetime.now()
            contact.unread_count = contact.unread_count + 1
            db.commit()
            logger.info(f"Updated contact {contact_id} activity")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error updating contact activity: {str(e)}")
