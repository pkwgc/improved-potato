"""
聊天处理模块 - 包含完整的聊天处理和订单处理集成功能

此模块提供以下功能：
1. 处理用户聊天请求
2. 调用AI服务生成回复
3. 检测下单意图并创建订单
4. 减少库存数量
"""

import logging
import time
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional

from flask import request, jsonify
from sqlalchemy.orm import Session

from database import User, Template, ChatMessage, Context, get_db
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL, MAX_TOKEN, TEMPERATURE, ENABLE_USER_PROFILE
from ai_service import AIService
from user_profile_extractor import update_user_profile_from_message, analyze_message_intent, extract_order_info
from order_processing import create_order_from_chat, extract_order_from_ai_response

logger = logging.getLogger(__name__)

def bind_template_to_db(db: Session, user_id: str, template_name: str, username: str = None) -> bool:
    """将模板绑定到用户
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        template_name: 模板名称
        username: 用户名（可选）
        
    Returns:
        绑定是否成功
    """
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            if not username:
                return False
                
            user = User(user_id=user_id, username=username)
            db.add(user)
            db.flush()
            
        user.template_name = template_name
        db.commit()
        return True
    except Exception as e:
        logger.error(f"绑定模板失败: {str(e)}")
        db.rollback()
        return False

def get_bound_template_from_db(db: Session, user_id: str) -> Optional[str]:
    """获取用户绑定的模板
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        模板名称，如果未绑定则返回None
    """
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user and user.template_name:
            return user.template_name
        return None
    except Exception as e:
        logger.error(f"获取绑定模板失败: {str(e)}")
        return None

def chat():
    """处理聊天请求，包括下单意图检测和订单处理"""
    try:
        data = request.get_json()
        if not data:
            logger.error(f"请求拒绝：非JSON格式请求 | IP: {request.remote_addr} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return jsonify({"error": "请求必须为 JSON 格式"}), 400

        user_id = data.get("user_id", "default_user")
        nameuser = data.get("nameuser", "anonymous")
        user_message = data.get("content")

        if not user_message:
            logger.error(f"请求拒绝：缺少content字段 | 用户ID: {user_id} | 用户名: {nameuser} | IP: {request.remote_addr} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return jsonify({"error": "Missing 'content' field"}), 400

        normalized_msg = str(user_message).strip()
        logger.info(f"用户消息：{normalized_msg} | 用户ID: {user_id} | 用户名: {nameuser} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        db = next(get_db())

        if normalized_msg == "查询模板":
            templates = db.query(Template).all()
            template_names = [template.name for template in templates]
            reply = "无可用模板" if not template_names else "、".join(template_names)
            return jsonify({
                "reply": reply,
                "trigger_api": False
            })

        if normalized_msg.startswith("切换模板-") and len(normalized_msg) > 5:
            template_name = normalized_msg.split("切换模板-")[1].strip()
            template = db.query(Template).filter(Template.name == template_name).first()

            if template:
                bind_template_to_db(db, user_id, template_name, nameuser)
                logger.info(f"模板绑定成功：{user_id} -> {template_name} | 用户名: {nameuser} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return jsonify({
                    "reply": f"模板已切换为：{template_name}",
                    "trigger_api": False
                })
            else:
                logger.warning(f"请求拒绝：模板不存在 | 模板名: {template_name} | 用户ID: {user_id} | 用户名: {nameuser} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return jsonify({
                    "reply": f"未找到模板：{template_name}，请使用\"查询模板\"查看可用列表",
                    "trigger_api": False
                })

        bound_template = get_bound_template_from_db(db, user_id)
        if not bound_template:
            bound_template = get_bound_template_from_db(db, nameuser)
            if not bound_template:
                logger.error(f"请求拒绝：用户未绑定模板 | 用户ID: {user_id} | 用户名: {nameuser} | 消息: {normalized_msg} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                try:
                    context = Context(user_id=user_id)
                    db.add(context)
                    db.flush()  # 获取context.id
                    
                    system_message = ChatMessage(
                        context_id=context.id,
                        user_id=user_id,
                        role="system",
                        content="请求拒绝：用户未绑定模板，请先绑定模板后继续使用",
                        tokens_used=0
                    )
                    db.add(system_message)
                    db.commit()
                except Exception as e:
                    logger.error(f"记录拒绝消息到数据库失败: {str(e)}")
                return jsonify({
                    "reply": "请先绑定模板，例如：切换模板-叶子评论；查询模板例如：查询模板",
                    "trigger_api": False
                })
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id, username=nameuser)
            db.add(user)
            db.commit()
        
        if ENABLE_USER_PROFILE:
            if analyze_message_intent(normalized_msg):
                logger.info(f"检测到用户信息分享意图: {user_id} | 消息: {normalized_msg[:30]}...")
                update_result = update_user_profile_from_message(db, user_id, normalized_msg)
                if update_result:
                    logger.info(f"已从消息中更新用户资料: {user_id}")
            
            elif "地址" in normalized_msg or "电话" in normalized_msg or "联系" in normalized_msg:
                order_info = extract_order_info(normalized_msg)
                if order_info:
                    logger.info(f"从订单消息中提取到用户信息: {user_id} | 信息: {order_info}")
                    update_result = update_user_profile_from_message(db, user_id, normalized_msg)
                    logger.info(f"从订单消息中更新用户资料: {user_id}, 结果: {update_result}")
        
        if hasattr(user, 'token_balance') and user.token_balance <= 0:
            logger.error(f"请求拒绝：Token余额不足 | 用户ID: {user_id} | 用户名: {nameuser} | 余额: {user.token_balance} | 消息: {normalized_msg} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                context = Context(user_id=user_id)
                db.add(context)
                db.flush()  # 获取context.id
                
                system_message = ChatMessage(
                    context_id=context.id,
                    user_id=user_id,
                    role="system",
                    content="请求拒绝：Token余额不足，请联系管理员充值",
                    tokens_used=0
                )
                db.add(system_message)
                db.commit()
            except Exception as e:
                logger.error(f"记录拒绝消息到数据库失败: {str(e)}")
                
            return jsonify({
                "reply": "您的Token余额不足，请联系管理员充值后继续使用。",
                "usage": {"total_tokens": 0}
            })
        
        from flask import current_app as app
        if not hasattr(app, '_ai_service_instance'):
            logger.info("创建AI服务单例...")
            app._ai_service_instance = AIService(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                model=MODEL,
                max_tokens=MAX_TOKEN,
                temperature=TEMPERATURE
            )
        
        ai_service = app._ai_service_instance
        
        chat_start_time = time.time()
        
        result = ai_service.process_chat(
            db=db,
            user_id=user_id,
            user_message=normalized_msg,
            template_name=bound_template,
            username=nameuser
        )
        
        if ENABLE_USER_PROFILE:
            if "raw_content" in result:
                try:
                    match = re.search(r'{.*}', result["raw_content"], re.DOTALL)
                    if match:
                        json_str = re.sub(r'(?<!\\)\\(?![\\/"bfnrtu])', r'\\\\', match.group())
                        raw_json = json.loads(json_str)
                        logger.info(f"从[AI 原始回复内容]中提取到JSON: {user_id}")
                        update_result = update_user_profile_from_message(db, user_id, normalized_msg, raw_json)
                        logger.info(f"已从原始回复内容更新用户资料: {user_id}, 结果: {update_result}")
                except Exception as e:
                    logger.error(f"从原始回复内容提取用户信息失败: {str(e)}")
                    if "user_info" in result or "user_preferences" in result or \
                       (result.get("trigger_api") == True and "slots" in result):
                        logger.info(f"回退: 从处理后的AI回复中检测到用户信息: {user_id}")
                        update_result = update_user_profile_from_message(db, user_id, normalized_msg, result)
                        logger.info(f"已从处理后的AI回复更新用户资料: {user_id}, 结果: {update_result}")
            elif "user_info" in result or "user_preferences" in result or \
                 (result.get("trigger_api") == True and "slots" in result):
                logger.info(f"从处理后的AI回复中检测到用户信息: {user_id}")
                update_result = update_user_profile_from_message(db, user_id, normalized_msg, result)
                logger.info(f"已从处理后的AI回复更新用户资料: {user_id}, 结果: {update_result}")
        
        response_time = time.time() - chat_start_time
        logger.info(f"AI响应总时间: {response_time:.2f}秒 | 用户ID: {user_id}")
        
        if isinstance(result, dict):
            result["response_time"] = response_time
        
        try:
            reply = result.get("reply", "")
            
            has_order_intent = False
            order_intent_keywords = ["我想买", "我要买", "我想订", "我要订", "帮我买", "帮我订", "购买", "下单"]
            for keyword in order_intent_keywords:
                if keyword in normalized_msg:
                    has_order_intent = True
                    logger.info(f"检测到用户下单意图: {user_id}, 关键词: {keyword}")
                    break
            
            order_success_keywords = ["下单成功", "订单已创建", "已为您下单", "已完成下单", "订单已生成", 
                                     "购买成功", "已购买", "已帮您购买", "已帮您下单"]
            
            order_success = False
            for keyword in order_success_keywords:
                if keyword in reply:
                    order_success = True
                    logger.info(f"检测到AI回复中的下单成功关键词: {user_id}, 关键词: {keyword}")
                    break
            
            if has_order_intent and order_success:
                logger.info(f"尝试创建订单: {user_id}")
                
                order = create_order_from_chat(db, user_id, result)
                
                if order:
                    logger.info(f"成功创建订单: {order.order_number}, 用户: {user_id}")
                    result["order_created"] = True
                    result["order_number"] = order.order_number
                    result["order_total"] = order.total_amount
                    
                    if f"订单号" not in reply and f"订单编号" not in reply:
                        order_info_text = f"\n\n您的订单已创建成功！订单号: {order.order_number}, 总金额: ¥{order.total_amount:.2f}"
                        result["reply"] = reply + order_info_text
                else:
                    logger.warning(f"创建订单失败: {user_id}")
        except Exception as e:
            import traceback
            logger.error(f"处理订单创建出错: {str(e)}\n{traceback.format_exc()}")
        
        stream = request.args.get('stream', 'false').lower() == 'true'
        if stream:
            logger.warning("Stream requested but not supported, falling back to regular response")
            return jsonify(result)
        
        return jsonify(result)

    except Exception as e:
        import traceback
        logger.error(f"处理出错：{str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        if 'db' in locals():
            db.close()
