from flask import request, jsonify
from database import get_db, WechatMessage, WechatContact, User
import logging
from datetime import datetime
import time
import json

logger = logging.getLogger(__name__)

def register_api_send_message(app, socketio=None):
    @app.route('/api/send_message', methods=['POST'])
    def send_message():
        """发送消息到联系人"""
        logger.info("收到发送消息请求")
        try:
            data = request.json
            logger.debug(f"请求数据: {data}")
            if not data:
                logger.warning("请求体不是JSON格式")
                return jsonify({"error": "请求必须为JSON格式"}), 400

            owner_id = data.get('owner_id')
            contact_ids = data.get('contact_ids', [])
            content = data.get('content')
            wechat_id = data.get('wechat_id')
            content_type = data.get('content_type', 'text')

            logger.debug(f"参数校验 owner_id={owner_id}, contact_ids={contact_ids}, content={content}")
            if not owner_id or not contact_ids or not content:
                logger.warning(f"缺少参数: owner_id={owner_id}, contact_ids={contact_ids}, content={content}")
                return jsonify({"error": "缺少必要参数"}), 400

            db = next(get_db())
            logger.debug(f"数据库连接成功")

            contacts = db.query(WechatContact).filter(
                WechatContact.id.in_(contact_ids)
            ).all()
            logger.debug(f"查询联系人结果: {contacts}")
            if not contacts:
                logger.warning(f"未找到联系人: {contact_ids}")
                return jsonify({"error": "未找到指定联系人"}), 404

            owner = db.query(User).filter(User.user_id == owner_id).first()
            if not owner:
                logger.warning(f"发送者不存在: {owner_id}")
                return jsonify({"error": "发送者不存在"}), 404

            sent_messages = []

            for contact in contacts:
                unique_message_id = f"{owner_id}_{int(time.time() * 1000)}_{hash(content)}"
                logger.info(f"正在处理联系人: {contact.id}（{contact.nickname or contact.wechat_id}）")
                message = WechatMessage(
                    message_id=unique_message_id,
                    contact_id=contact.id,
                    sender_id=wechat_id,
                    content=content,
                    content_type=content_type,
                    is_from_ai=False,
                    status="sent",
                    created_at=datetime.now()
                )
                db.flush()
                contact.last_active_at = message.created_at

                logger.debug(f"消息对象已添加，ID: {message.id}")

                message_info = {
                    "id": message.id,
                    "contact_id": contact.id,
                    "contact_name": contact.nickname or contact.wechat_id,
                    "status": "sent"
                }
                sent_messages.append(message_info)
                
                if socketio:
                    try:
                        parent_contact = None
                        if contact.parent_id:
                            parent_contact = db.query(WechatContact).filter(
                                WechatContact.id == contact.parent_id
                            ).first()
                        else:
                            parent_contact = contact
                        logger.debug(f"推送消息 parent_contact: {parent_contact}")
                        if parent_contact:
                            ws_message = {
                                "id": unique_message_id,
                                "type": "message",
                                "content": content,
                                "content_type": content_type,
                                "sender": {
                                    "id": wechat_id,
                                    "name": owner.username
                                },
                                "receiver": {
                                    "id": contact.wechat_id,
                                    "name": contact.nickname or contact.wechat_id,
                                    "is_group": contact.is_group
                                },
                                "timestamp": datetime.now().isoformat(),
                                "require_ack": True
                            }
                            room_id = f"wechat_{parent_contact.wechat_id}"

                            logger.info(
                                f"推送WebSocket消息到房间: {room_id}, 内容: {json.dumps(ws_message, ensure_ascii=False)}")
                            socketio.emit('new_message', ws_message, to=room_id)

                    except Exception as e:
                        logger.error(f"通过WebSocket推送消息失败: {str(e)}")

            db.commit()
            logger.info(f"所有消息处理完毕，共发送: {len(sent_messages)} 条，详情: {sent_messages}")
            return jsonify({
                "success": True,
                "messages": sent_messages
            })
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return jsonify({"error": "服务器内部错误"}), 500

    @app.route('/api/broadcast_message', methods=['POST'])
    def broadcast_message():
        """广播消息到多个微信账号"""
        try:
            data = request.json
            if not data:
                return jsonify({"error": "请求必须为JSON格式"}), 400
                
            sender_id = data.get('sender_id')
            wechat_ids = data.get('wechat_ids', [])
            content = data.get('content')
            content_type = data.get('content_type', 'text')
            
            if not sender_id or not wechat_ids or not content:
                return jsonify({"error": "缺少必要参数"}), 400
                
            if socketio:
                try:
                    db = next(get_db())
                    sender = db.query(User).filter(User.user_id == sender_id).first()
                    
                    if not sender:
                        return jsonify({"error": "发送者不存在"}), 404
                        
                    broadcast_results = []
                    
                    for wechat_id in wechat_ids:
                        ws_message = {
                            "id": f"broadcast_{sender_id}_{wechat_id}_{int(time.time()*1000)}",
                            "type": "broadcast",
                            "content": content,
                            "content_type": content_type,
                            "sender": {
                                "id": sender_id,
                                "name": sender.username
                            },
                            "timestamp": datetime.now().isoformat(),
                            "require_ack": True
                        }
                        
                        room_id = f"wechat_{wechat_id}"
                        socketio.emit('broadcast_message', ws_message, to=room_id)
                        
                        broadcast_results.append({
                            "wechat_id": wechat_id,
                            "status": "sent"
                        })
                        
                        logger.info(f"广播消息已发送到微信账号 {wechat_id}")
                        
                    return jsonify({
                        "success": True,
                        "broadcasts": broadcast_results
                    })
                except Exception as e:
                    logger.error(f"广播消息失败: {str(e)}")
                    return jsonify({"error": f"广播消息失败: {str(e)}"}), 500
            else:
                return jsonify({"error": "WebSocket未启用，无法广播消息"}), 400
        except Exception as e:
            logger.error(f"广播消息失败: {str(e)}")
            return jsonify({"error": "服务器内部错误"}), 500
