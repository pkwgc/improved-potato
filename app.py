from flask import Flask, request, jsonify, render_template, redirect, url_for, session, Response, make_response, \
    send_file
from openai import OpenAI
import os
import sys
import json
from decimal import Decimal
import re
import ast
import requests
import time
import io
import csv
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from decimal_json_encoder import decimal_json_dumps
from database import (
    get_db, create_tables, User, Template, Context, BillingRecord, AIFeedingRecord,
    load_context_from_db, save_context_to_db, get_bound_template_from_db,
    bind_template_to_db, load_user_prompt_from_db, record_billing, record_ai_feeding,
    Industry, Intent, TokenPackage, ChatMessage, UserTemplateBinding, InventoryUpload,
    InventoryItem, Order, OrderItem, Sale, WechatContact, WechatMessage, AIStrategy, KeywordFilter,
    Moment, MomentComment, IntentTracking, CustomerProfile, HumanAgent, ProactiveMessage, OperationLog
)
from security import rate_limit, request_validation, hmac_signature_required
from ai_api_client import AIService, recognize_intent, update_user_profile_from_message, analyze_message_intent, extract_order_info, extract_user_profile_info
from urllib.parse import quote_plus
from order_processing import extract_order_from_ai_response, create_order_from_chat, get_user_orders
from statistics_service import StatisticsService

from api_messages import register_api_messages
from api_send_message import register_api_send_message
from proactive_messaging import ProactiveMessagingService
from ai_api_client import CustomerProfilingService
from admin_required import admin_required, user_required

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL, MAX_TOKEN, TEMPERATURE,
    ENABLE_USER_PROFILE, ENABLE_PERSONALIZED_PROMPT, PERSONALIZED_PROMPT_TEMPLATE,
    CUSTOM_PLACEHOLDERS, CHAT_ACTIVE_MINUTES, GREETING_CONTEXT_MESSAGES,
    MAX_CONTEXT_LENGTH, MAX_CONTEXT_MESSAGES, AUTO_MESSAGE, ENABLE_AUTO_MESSAGE,
    MIN_COUNTDOWN_HOURS, MAX_COUNTDOWN_HOURS, NOON_QUIET_TIME_START,
    NOON_QUIET_TIME_END, EVENING_QUIET_TIME_START, EVENING_QUIET_TIME_END,
    IP_WHITELIST, IP_BLACKLIST, RATE_LIMIT_PER_MINUTE, TOKEN_LIMIT_DEFAULT,
    HAS_APPOINTMENT_DEFAULT, USER_PROFILE_PLACEHOLDER_PREFIX,
    USER_PROFILE_PLACEHOLDER_SUFFIX, ENABLE_JSON_STORAGE, CHAT_STORAGE_DIR,
    SYNC_DB_WITH_JSON, TOKEN_COST_RATE, TIME_COST_RATE, ADMIN_USERNAME,
    ADMIN_PASSWORD, ENABLE_IMAGE_RECOGNITION, ENABLE_EMOJI_RECOGNITION,
    ENABLE_SOCKET_IO, REDIS_URL, MAX_CONTACTS_PER_USER, ENABLE_AUTO_REGISTRATION,
    DEFAULT_MAX_WECHAT_ACCOUNTS, GLOBAL_MAX_WECHAT_ACCOUNTS, INTENT_LEVELS,
    PROACTIVE_FOLLOW_CONFIG
)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于会话管理
NEED_PROXY_PREFIX = [
    'http://shmmsns.qpic.cn',
    'https://shmmsns.qpic.cn',
    'http://thirdwx.qlogo.cn',
    'https://thirdwx.qlogo.cn',
    # 需要代理的域名继续加
]

def need_proxy(url):
    logger.info(f"客户端连接:3")
    return url and any(url.startswith(prefix) for prefix in NEED_PROXY_PREFIX)

# ===== Jinja2 模板过滤器 =====
@app.template_filter('proxy_url')
def proxy_url_filter(url):
    logger.info(f"客户端连接:2")
    if need_proxy(url):
        return f"/api/proxy?url={quote_plus(url)}"
    return url or ''

# ===== 图片代理接口 =====
@app.route('/api/proxy', methods=['GET'])
def proxy():
    logger.info(f"客户端连接:1")
    url = request.args.get('url')
    if not url:
        return 'No url', 400
    if not need_proxy(url):
        return 'Forbidden', 403
    try:
        r = requests.get(url, timeout=10)
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        return Response(r.content, mimetype=content_type)
    except Exception as e:
        return f'Error: {e}', 500

@app.template_filter('from_json')
def from_json_filter(value):
    """将JSON字符串转换为Python对象"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return value if value else []


from flask_socketio import SocketIO, emit, join_room, leave_room

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


register_api_messages(app)
register_api_send_message(app, socketio)

customer_profiling_service = CustomerProfilingService()
proactive_messaging_service = ProactiveMessagingService(socketio)

user_socket_map = {}  # 用户ID到socket ID的映射
user_last_heartbeat = {}  # 用户最后心跳时间
user_message_queues = {}  # 用户消息队列
user_wechat_rooms = {}  # 用户微信账号房间

from app_functions import setup_app_functions

setup_app_functions(app, user_message_queues, user_wechat_rooms)


@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    logger.info(f"客户端连接: {request.sid}")
    # 构造要发送的数据
    welcome_message = {
        "type": "system",
        "content": "欢迎连接到WebSocket服务器！",
        "timestamp": datetime.now().isoformat()
    }
    socketio.emit('new_message', welcome_message, to=request.sid)

    if not hasattr(app, 'cleanup_task_started'):
        app.cleanup_task_started = True

        def cleanup_task():
            from cleanup_task import cleanup_expired_connections
            while True:
                socketio.sleep(60)  # 每60秒执行一次
                cleanup_expired_connections(app, socketio, user_socket_map, user_last_heartbeat, user_message_queues)

        socketio.start_background_task(cleanup_task)


@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    disconnected_user = None
    for user_id, sid in user_socket_map.items():
        if sid == request.sid:
            disconnected_user = user_id
            user_socket_map.pop(user_id)
            if user_id in user_last_heartbeat:
                user_last_heartbeat.pop(user_id)
            logger.info(f"用户 {user_id} 断开连接")
            break


from config import load_config_from_file

load_config_from_file()


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)  # 实际 exe 所在目录
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
CONFIG_PATH = os.path.join(BASE_DIR, 'config.py')
PROMPT_DIR = os.path.join(BASE_DIR, 'prompts')

os.makedirs(PROMPT_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config():
    config = {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                match = re.match(r"^(\w+)\s*=\s*(.+)$", line)
                if match:
                    var_name, var_value_str = match.groups()
                    try:
                        var_value = ast.literal_eval(var_value_str)
                        config[var_name] = var_value
                    except:
                        config[var_name] = var_value_str
    except FileNotFoundError:
        logger.error(f"配置文件 `{CONFIG_PATH}` 不存在！")
        return {}
    return config


CONFIG = load_config()


def fix_invalid_backslashes(text):
    return re.sub(r'(?<!\\)\\(?![\\/"bfnrtu])', r'\\\\', text)


def extract_reply_and_confidence(content):
    """从AI回复中提取回复内容、置信度和意图信息"""
    reply = content
    confidence = 0
    intent_data = {"trigger_api": False, "intent_type": "no_intent"}

    try:
        json_content = None
        match = re.search(r'```json\s*({[\s\S]*?})\s*```', content, re.DOTALL)
        if match:
            json_content = match.group(1)
        else:
            match = re.search(r'{[\s\S]*?}', content, re.DOTALL)
            if match:
                json_content = match.group(0)

        if json_content:
            json_str = fix_invalid_backslashes(json_content)
            parsed = json.loads(json_str)

            reply = parsed.get("reply", content)
            intent_type = parsed.get("intent_type", "no_intent")
            intent_details = parsed.get("intent_details", {})
            confidence = intent_details.get("confidence", 0.0)

            if intent_type == "specific_intent":
                intent_name = intent_details.get("name")
                entities = intent_details.get("entities", {})

                trigger_api = False
                api_name = ""

                if intent_name in ["下单", "查询库存", "查询价格", "查询订单"]:
                    trigger_api = True
                    api_name = f"{intent_name}_api"

                intent_data = {
                    "trigger_api": trigger_api,
                    "intent": intent_name,
                    "industry": "",
                    "api": api_name,
                    "slots": entities,
                    "confidence": confidence,
                    "intent_type": intent_type
                }

                if "order_info" in parsed:
                    intent_data["order_info"] = parsed.get("order_info")

                if "user_info_detected" in parsed:
                    intent_data["user_info"] = parsed.get("user_info_detected")
            else:
                intent_data = {
                    "trigger_api": False,
                    "intent_type": intent_type
                }

                if "user_info_detected" in parsed:
                    intent_data["user_info"] = parsed.get("user_info_detected")
    except Exception as e:
        logger.warning(f"reply/confidence/intent 提取失败：{e}")

    return reply, confidence, intent_data


@app.route('/api/initial_sync', methods=['POST'])
@rate_limit()
@hmac_signature_required
@request_validation(required_fields=["user_id", "user_wxid", "wechat_id", "moments"])
def initial_sync():
    """微信朋友圈AI画像&归类接口"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        user_wxid = data.get("user_wxid")
        wechat_id = data.get("wechat_id")
        moments = data.get("moments", [])
        
        logger.info(f"开始处理用户 {user_id} 的朋友圈AI画像分析，朋友圈数量: {len(moments)}")
        
        db = next(get_db())
        
        all_moments_content = []
        for moment_data in moments:
            try:
                moment_content = {
                    "nickname": moment_data.get('nickname', ''),
                    "title": moment_data.get('title', ''),
                    "content": moment_data.get('content', ''),
                    "likes": moment_data.get('likes', []),
                    "comments": moment_data.get('comments', []),
                    "clicks": moment_data.get('clicks', 0),
                    "user_actions": moment_data.get('user_actions', [])
                }
                all_moments_content.append(moment_content)
                
                moment = Moment(
                    owner_id=1,
                    wechat_id=wechat_id,
                    content=moment_data.get('content', ''),
                    media_urls=json.dumps(moment_data.get('images', [])),
                    created_at=datetime.utcnow()
                )
                db.add(moment)
                
            except Exception as e:
                logger.error(f"处理朋友圈数据失败: {str(e)}")
                continue
        
        profile_result = {"summary": "", "labels": [], "category": "普通客户", "hobbies": []}
        
        if all_moments_content:
            try:
                ai_strategy = db.query(AIStrategy).filter_by(name="朋友圈画像分析").first()
                if not ai_strategy:
                    ai_strategy = AIStrategy(
                        name="朋友圈画像分析",
                        description="用于分析微信朋友圈内容生成用户画像",
                        prompt_template="""请分析以下微信朋友圈内容，生成用户画像：

朋友圈内容：
{moments_content}

请根据以上内容分析用户特征，并以JSON格式返回：
{{
  "summary": "用户画像摘要描述",
  "labels": ["标签1", "标签2", "标签3"],
  "category": "客户分组归类（高价值客户/中价值客户/普通客户/潜力客户）",
  "hobbies": ["兴趣爱好1", "兴趣爱好2", "兴趣爱好3"]
}}""",
                        system_message="你是专业的用户画像分析师，请根据用户的朋友圈内容分析其特征和兴趣。",
                        temperature=0.7,
                        max_tokens=2000
                    )
                    db.add(ai_strategy)
                    db.commit()
                
                moments_text = json.dumps(all_moments_content, ensure_ascii=False, indent=2)
                prompt = ai_strategy.prompt_template.replace("{moments_content}", moments_text)
                
                from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL
                import requests
                
                response = requests.post(
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": MODEL,
                        "messages": [
                            {"role": "system", "content": ai_strategy.system_message},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": ai_strategy.temperature,
                        "max_tokens": ai_strategy.max_tokens
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    ai_result = response.json()
                    if "choices" in ai_result and ai_result["choices"]:
                        content = ai_result["choices"][0]["message"]["content"]
                        try:
                            import re
                            json_match = re.search(r'\{.*\}', content, re.DOTALL)
                            if json_match:
                                profile_data = json.loads(json_match.group())
                                profile_result = {
                                    "summary": profile_data.get("summary", ""),
                                    "labels": profile_data.get("labels", []),
                                    "category": profile_data.get("category", "普通客户"),
                                    "hobbies": profile_data.get("hobbies", [])
                                }
                        except json.JSONDecodeError:
                            logger.error("AI返回内容无法解析为JSON")
                
            except Exception as ai_error:
                logger.error(f"AI画像分析失败: {str(ai_error)}")
        
        contact = db.query(WechatContact).filter_by(wechat_id=wechat_id).first()
        if not contact:
            contact = WechatContact(
                owner_id=1,
                wechat_id=wechat_id,
                nickname=wechat_id,
                created_at=datetime.utcnow()
            )
            db.add(contact)
            db.commit()
        
        customer_profile = db.query(CustomerProfile).filter_by(contact_id=contact.id).first()
        if not customer_profile:
            customer_profile = CustomerProfile(
                contact_id=contact.id,
                profile_type="综合画像",
                profile_value=json.dumps(profile_result, ensure_ascii=False),
                confidence=0.8,
                value_level=profile_result.get("category", "普通客户"),
                activity_score=0.7,
                created_at=datetime.utcnow()
            )
            db.add(customer_profile)
        else:
            customer_profile.profile_value = json.dumps(profile_result, ensure_ascii=False)
            customer_profile.value_level = profile_result.get("category", "普通客户")
            customer_profile.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"朋友圈AI画像分析完成 - 用户: {user_id}")
        
        return jsonify({
            "success": True,
            "profile": profile_result
        })
        
    except Exception as e:
        logger.error(f"朋友圈AI画像分析失败: {str(e)}")
        if 'db' in locals():
            db.rollback()
        return jsonify({"error": f"画像分析失败: {str(e)}"}), 500
    finally:
        if 'db' in locals():
            db.close()


@app.route('/api/profile/update', methods=['POST'])
@rate_limit()
@hmac_signature_required
@request_validation(required_fields=["user_id", "profile_data"])
def profile_update():
    """用户画像数据上报接口"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        profile_data = data.get("profile_data")
        
        logger.info(f"收到用户 {user_id} 的画像更新请求")
        
        ai_service = AIService()
        result = ai_service.update_user_profile(
            user_id=user_id,
            profile_data=profile_data
        )
        
        if result.get('success'):
            db = next(get_db())
            try:
                customer_profile = db.query(CustomerProfile).filter_by(user_id=user_id).first()
                
                if not customer_profile:
                    customer_profile = CustomerProfile(
                        user_id=user_id,
                        interests=json.dumps(profile_data.get('interests', [])),
                        activity_score=profile_data.get('activity_score', 0.5),
                        value_level=profile_data.get('value_level', '潜在用户'),
                        conversion_rate=profile_data.get('conversion_rate', 0.0),
                        created_at=datetime.utcnow()
                    )
                    db.add(customer_profile)
                else:
                    if 'interests' in profile_data:
                        customer_profile.interests = json.dumps(profile_data['interests'])
                    if 'activity_score' in profile_data:
                        customer_profile.activity_score = profile_data['activity_score']
                    if 'value_level' in profile_data:
                        customer_profile.value_level = profile_data['value_level']
                    if 'conversion_rate' in profile_data:
                        customer_profile.conversion_rate = profile_data['conversion_rate']
                    customer_profile.updated_at = datetime.utcnow()
                
                db.commit()
                logger.info(f"用户 {user_id} 画像更新成功")
                
            finally:
                db.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"用户画像更新失败: {str(e)}")
        return jsonify({"error": f"画像更新失败: {str(e)}"}), 500


@app.route('/api/chat', methods=['POST'])
@rate_limit()  # Uses RATE_LIMIT_PER_MINUTE from config.py
@request_validation(required_fields=["user_id", "content"])
def chat():
    """处理聊天请求，包括下单意图检测和订单处理"""
    db = None
    try:
        data = request.get_json()
        if not data:
            logger.error(
                f"请求拒绝：非JSON格式请求 | IP: {request.remote_addr} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return jsonify({"error": "请求必须为 JSON 格式"}), 400

        user_id = data.get("user_id", "default_user")
        nameuser = data.get("nameuser", "anonymous")
        user_message = data.get("content")
        contact_id = data.get("contact_id")

        if not user_message:
            logger.error(
                f"请求拒绝：缺少content字段 | 用户ID: {user_id} | 用户名: {nameuser} | IP: {request.remote_addr} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return jsonify({"error": "Missing 'content' field"}), 400

        normalized_msg = str(user_message).strip()

        def log_rejection_and_save_system_message(db, user_id, message):
            logger.error(message)
            try:
                context = Context(user_id=user_id)
                db.add(context)
                db.flush()

                system_message = ChatMessage(
                    context_id=context.id,
                    user_id=user_id,
                    role="system",
                    content=message,
                    tokens_used=0
                )
                db.add(system_message)
                db.commit()
            except Exception as e:
                logger.error(f"记录拒绝消息到数据库失败: {str(e)}")

        db = next(get_db())

        if contact_id:
            contact = db.query(WechatContact).filter(WechatContact.wechat_id == contact_id).first()
            if contact and not contact.ai_reply_enabled:
                logger.info(f"AI回复已禁用dd | 用户ID: {user_id} | 联系人ID: {contact_id}")
                return jsonify({
                    "reply": "",
                    "message": "AI回复已禁用",
                    "trigger_api": False
                })
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            if not ENABLE_AUTO_REGISTRATION:
                rejection_msg = f"请求拒绝：用户未注册且自动注册已禁用 | 用户ID: {user_id} | 用户名: {nameuser} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                log_rejection_and_save_system_message(db, user_id, rejection_msg)
                return jsonify({
                    "reply": "您的账号未注册，请联系管理员开通账号后使用。",
                    "trigger_api": False
                })
            user = User(user_id=user_id, username=nameuser)
            db.add(user)
            db.commit()

        if normalized_msg == "查询模板":
            template_names = [template.name for template in db.query(Template).all()]
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
                logger.info(
                    f"模板绑定成功：{user_id} -> {template_name} | 用户名: {nameuser} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return jsonify({
                    "reply": f"模板已切换为：{template_name}",
                    "trigger_api": False
                })
            else:
                logger.warning(
                    f"请求拒绝：模板不存在 | 模板名: {template_name} | 用户ID: {user_id} | 用户名: {nameuser} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return jsonify({
                    "reply": f"未找到模板：{template_name}，请使用\"查询模板\"查看可用列表",
                    "trigger_api": False
                })

        bound_template = get_bound_template_from_db(db, user_id)
        if not bound_template:
            bound_template = get_bound_template_from_db(db, nameuser)
            if not bound_template:
                rejection_msg = f"请求拒绝：用户未绑定模板 | 用户ID: {user_id} | 用户名: {nameuser} | 消息: {normalized_msg} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                log_rejection_and_save_system_message(db, user_id, rejection_msg)

                return jsonify({
                    "reply": "请先绑定模板，例如：切换模板-叶子评论；查询模板例如：查询模板",
                    "trigger_api": False
                })



        if ENABLE_USER_PROFILE:
            if analyze_message_intent(normalized_msg):
                logger.info(f"检测到用户信息分享意图: {user_id} | 消息: {normalized_msg[:30]}...")
                update_result = update_user_profile_from_message(db, user_id, normalized_msg)
                if update_result:
                    logger.info(f"已从消息中更新用户资料: {user_id}")

            elif any(keyword in normalized_msg for keyword in ["地址", "电话", "联系"]):
                order_info = extract_order_info(normalized_msg)
                if order_info:
                    logger.info(f"从订单消息中提取到用户信息: {user_id} | 信息: {order_info}")
                    update_result = update_user_profile_from_message(db, user_id, normalized_msg)
                    logger.info(f"从订单消息中更新用户资料: {user_id}, 结果: {update_result}")

        from config import CONFIG
        max_request_size = CONFIG.get('MAX_REQUEST_SIZE', 4096)
        if len(normalized_msg) > max_request_size:
            rejection_msg = f"请求拒绝：消息长度超过限制 | 用户ID: {user_id} | 用户名: {nameuser} | 消息长度: {len(normalized_msg)} | 限制: {max_request_size} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            log_rejection_and_save_system_message(db, user_id, rejection_msg)

            return jsonify({
                "reply": f"您的消息长度超过限制（最大{max_request_size}字符），请缩短后重试。",
                "usage": {"total_tokens": 0}
            })

        if CONFIG.get('ENABLE_USER_SPECIFIC_LIMITS', False):
            max_daily_requests = CONFIG.get('MAX_DAILY_REQUESTS_PER_USER', 1000)
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_requests = db.query(BillingRecord).filter(
                BillingRecord.user_id == user_id,
                BillingRecord.created_at >= today_start
            ).count()

            if today_requests >= max_daily_requests:
                rejection_msg = f"请求拒绝：用户今日请求次数已达上限 | 用户ID: {user_id} | 用户名: {nameuser} | 今日请求数: {today_requests} | 限制: {max_daily_requests} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                log_rejection_and_save_system_message(db, user_id, rejection_msg)

                return jsonify({
                    "reply": f"您今日请求次数已达上限（{max_daily_requests}次），请明日再试。",
                    "usage": {"total_tokens": 0}
                })

        if hasattr(user, 'token_balance') and user.token_balance <= 0:
            rejection_msg = f"请求拒绝：Token余额不足 | 用户ID: {user_id} | 用户名: {nameuser} | 余额: {user.token_balance} | 消息: {normalized_msg} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            log_rejection_and_save_system_message(db, user_id, rejection_msg)

            return jsonify({
                "reply": "您的Token余额不足，请联系管理员充值后继续使用。",
                "usage": {"total_tokens": 0}
            })

        ai_service = getattr(app, '_ai_service_instance', None)
        if ai_service is None:
            with app.app_context():
                ai_service = AIService(
                    api_key=DEEPSEEK_API_KEY,
                    base_url=DEEPSEEK_BASE_URL,
                    model=MODEL,
                    max_tokens=MAX_TOKEN,
                    temperature=TEMPERATURE
                )
                app._ai_service_instance = ai_service
                logger.info("创建AI服务单例...")

        chat_start_time = time.time()

        try:
            from inventory_processor import debug_inventory_items_with_notes
            debug_inventory_items_with_notes(db, user_id)
        except Exception as e:
            logger.error(f"调试库存商品备注失败: {str(e)}")

        result = ai_service.process_chat(
            db=db,
            user_id=user_id,
            user_message=normalized_msg,
            template_name=bound_template,
            username=nameuser
        )

        if "intent_data" in result and result["intent_data"]:
            intent_data = result["intent_data"]
            if intent_data.get("intent_type") == "specific_intent":
                intent_name = intent_data.get("intent", "")
                confidence = intent_data.get("confidence", 0.0)

                try:
                    contact = db.query(WechatContact).filter(WechatContact.wechat_id == contact_id).first() if contact_id else None

                    intent_tracking = IntentTracking(
                        user_id=user.id,
                        contact_id=contact.id if contact else None,
                        intent_type=intent_name,
                        confidence_score=confidence,
                        context_data=json.dumps(intent_data, ensure_ascii=False),
                        source='AI'
                    )
                    db.add(intent_tracking)

                    if confidence > 0.8 and intent_name in ["下单", "购买意向"]:
                        human_agents = db.query(HumanAgent).filter(
                            HumanAgent.owner_id == user.id,
                            HumanAgent.is_active == True
                        ).order_by(HumanAgent.priority).all()

                        if human_agents:
                            for agent in human_agents:
                                notification_data = {
                                    "type": "human_handoff",
                                    "customer_id": user_id,
                                    "customer_name": nameuser,
                                    "intent": intent_name,
                                    "confidence": confidence,
                                    "message": normalized_msg,
                                    "timestamp": datetime.now().isoformat()
                                }
                                socketio.emit('human_handoff_notification',
                                              notification_data,
                                              to=f"wechat_{agent.agent_wechat_id}")

                    db.commit()
                except Exception as e:
                    logger.error(f"记录意向跟踪失败: {str(e)}")

        if ENABLE_USER_PROFILE:
            if "raw_content" in result:
                try:
                    raw_json = json.loads(result["raw_content"])
                    logger.info(f"从[AI 原始回复内容]中提取到JSON: {user_id}")
                    update_result = update_user_profile_from_message(db, user_id, normalized_msg, raw_json)
                    logger.info(f"已从原始回复内容更新用户资料: {user_id}, 结果: {update_result}")
                except json.JSONDecodeError:
                    logger.warning("原始内容无法解析为 JSON，尝试回退处理")
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
            intent = result.get("intent", "")
            trigger_api = result.get("trigger_api", False)
            api = result.get("api", "")

            logger.info(f"检查订单意图: intent={intent}, trigger_api={trigger_api}, api={api}")

            def process_order_creation(has_order_intent, order_success, result):
                if has_order_intent and order_success:
                    logger.info(f"尝试创建订单: {user_id}")

                    order = create_order_from_chat(db, user_id, result)

                    if order:
                        logger.info(f"成功创建订单: {order.order_number}, 用户: {user_id}")
                        result["order_created"] = True
                        result["order_number"] = order.order_number
                        result["order_total"] = order.total_amount

                        reply = result.get("reply", "")

                        if f"订单号" not in reply and f"订单编号" not in reply:
                            order_info_text = f"\n\n您的订单已创建成功！订单号: {order.order_number}, 总金额: ¥{order.total_amount:.2f}"
                            result["reply"] = reply + order_info_text
                    else:
                        logger.warning(f"创建订单失败: {user_id}")

            if intent == "购买商品" and trigger_api and (api == "order_processing" or not api):
                logger.info(f"检测到结构化购买意图: {user_id}, intent={intent}")

                slots = result.get("slots", {})
                if slots:
                    logger.info(f"从slots中提取订单信息: {slots}")

                    order = create_order_from_chat(db, user_id, result)

                    if order:
                        logger.info(f"成功创建订单: {order.order_number}, 用户: {user_id}")
                        result["order_created"] = True
                        result["order_number"] = order.order_number
                        result["order_total"] = order.total_amount

                        reply = result.get("reply", "")

                        if f"订单号" not in reply and f"订单编号" not in reply:
                            order_info_text = f"\n\n您的订单已创建成功！订单号: {order.order_number}, 总金额: ¥{order.total_amount:.2f}"
                            result["reply"] = reply + order_info_text
                    else:
                        logger.warning(f"创建订单失败: {user_id}")
            else:
                reply = result.get("reply", "")

                order_intent_keywords = ["我想买", "我要买", "我想订", "我要订", "帮我买", "帮我订", "购买", "下单"]
                has_order_intent = any(keyword in normalized_msg for keyword in order_intent_keywords)
                if has_order_intent:
                    logger.info(f"检测到用户下单意图: {user_id}")

                order_success_keywords = ["下单成功", "订单已创建", "已为您下单", "已完成下单", "订单已生成",
                                          "购买成功", "已购买", "已帮您购买", "已帮您下单", "已帮您下单"]
                order_success = any(keyword in reply for keyword in order_success_keywords)
                if order_success:
                    logger.info(f"检测到AI回复中的下单成功关键词: {user_id}")

                process_order_creation(has_order_intent, order_success, result)

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
        if db is not None:
            db.close()



from flask import Flask, request, jsonify
from datetime import datetime


# ... 你的其他 import


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))

        return render_template('login.html', error='用户名或密码错误')

    return render_template('login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        stats_service = StatisticsService(db)
        stats = stats_service.get_dashboard_stats()

        templates = db.query(Template).all()

        return render_template(
            'dashboard.html',
            user_count=stats['user_count'],
            total_tokens=stats['total_tokens'],
            total_duration=stats['total_duration'],
            total_cost=stats['total_revenue'],
            active_users_today=stats['active_users_today'],
            active_users_week=stats['active_users_week'],
            active_users_month=stats['active_users_month'],
            total_conversations=stats['total_conversations'],
            token_usage_labels=stats['token_usage_labels'],
            token_usage_data=stats['token_usage_data'],
            active_users_labels=stats['active_users_labels'],
            active_users_data=stats['active_users_data'],
            template_usage_labels=stats['template_usage_labels'],
            template_usage_data=stats['template_usage_data'],
            industry_labels=stats['industry_labels'],
            industry_data=stats['industry_data'],
            templates=templates,
            now=datetime.now()
        )
    finally:
        db.close()


@app.route('/admin/users')
def admin_users():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:

        stats_service = StatisticsService(db)
        dashboard_stats = stats_service.get_dashboard_stats()

        page = request.args.get('page', 1, type=int)
        per_page = 10
        search = request.args.get('search', '')
        filter_type = request.args.get('filter', 'all')
        sort_type = request.args.get('sort', 'recent')

        query = db.query(User)

        if search:
            query = query.filter(
                (User.username.like(f'%{search}%')) |
                (User.user_id.like(f'%{search}%'))
            )

        if filter_type == 'active':
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            active_user_ids = db.query(BillingRecord.user_id).distinct().filter(
                BillingRecord.created_at >= seven_days_ago
            ).all()
            active_user_ids = [user_id[0] for user_id in active_user_ids]
            query = query.filter(User.user_id.in_(active_user_ids))
        elif filter_type == 'inactive':
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            active_user_ids = db.query(BillingRecord.user_id).distinct().filter(
                BillingRecord.created_at >= seven_days_ago
            ).all()
            active_user_ids = [user_id[0] for user_id in active_user_ids]
            query = query.filter(~User.user_id.in_(active_user_ids))
        elif filter_type == 'appointment':
            query = query.filter(User.has_appointment == True)

        if sort_type == 'tokens':
            user_tokens = db.query(
                BillingRecord.user_id,
                func.sum(BillingRecord.tokens_used).label('total_tokens')
            ).group_by(BillingRecord.user_id).subquery()

            query = query.outerjoin(
                user_tokens, User.user_id == user_tokens.c.user_id
            ).order_by(desc(user_tokens.c.total_tokens))
        elif sort_type == 'duration':
            user_duration = db.query(
                BillingRecord.user_id,
                func.sum(BillingRecord.duration_seconds).label('total_duration')
            ).group_by(BillingRecord.user_id).subquery()

            query = query.outerjoin(
                user_duration, User.user_id == user_duration.c.user_id
            ).order_by(desc(user_duration.c.total_duration))
        else:
            user_recent = db.query(
                BillingRecord.user_id,
                func.max(BillingRecord.created_at).label('last_active')
            ).group_by(BillingRecord.user_id).subquery()

            query = query.outerjoin(
                user_recent, User.user_id == user_recent.c.user_id
            ).order_by(desc(user_recent.c.last_active))

        total_users = query.count()
        total_pages = (total_users + per_page - 1) // per_page

        users = query.offset((page - 1) * per_page).limit(per_page).all()

        templates = db.query(Template).all()

        user_data = []
        for user in users:
            user_stats = stats_service.get_user_stats(user_id=user.user_id)
            template_name = get_bound_template_from_db(db, user.user_id)

            user_data.append({
                'id': user.id,
                'user_id': user.user_id,
                'username': user.username,
                'template': template_name,
                'tokens': user_stats.get('total_tokens', 0) if user_stats else 0,
                'token_balance': user_stats.get('token_balance', 0) if user_stats else 0,
                'token_limit': user_stats.get('token_limit', 0) if user_stats else 0,
                'token_package': user_stats.get('token_package', '') if user_stats else '',
                'duration': user_stats.get('total_duration', 0) if user_stats else 0,
                'conversations': user_stats.get('total_conversations', 0) if user_stats else 0,
                'active_days': user_stats.get('active_days', 0) if user_stats else 0,
                'avg_response_time': user_stats.get('avg_response_time', 0) if user_stats else 0,
                'has_appointment': user_stats.get('has_appointment', False) if user_stats else False
            })

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        avg_response_time = 0
        if dashboard_stats.get('total_duration', 0) > 0 and dashboard_stats.get('total_conversations', 0) > 0:
            avg_response_time = dashboard_stats.get('total_duration', 0) / dashboard_stats.get('total_conversations', 1)

        return render_template(
            'users.html',
            users=user_data,
            message=message,
            message_type=message_type,
            total_users=dashboard_stats.get('user_count', 0),
            total_tokens=dashboard_stats.get('total_tokens', 0),
            active_users_count=dashboard_stats.get('active_users_week', 0),
            avg_response_time=avg_response_time,
            token_usage_labels=dashboard_stats.get('token_usage_labels', []),
            token_usage_data=dashboard_stats.get('token_usage_data', []),
            template_usage_labels=dashboard_stats.get('template_usage_labels', []),
            template_usage_data=dashboard_stats.get('template_usage_data', []),
            current_page=page,
            total_pages=total_pages,
            templates=templates
        )
    finally:
        db.close()


@app.route('/admin/templates', methods=['GET', 'POST'])
def admin_templates():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'add':
                name = request.form.get('name')
                content = request.form.get('content')
                template_type = request.form.get('template_type', 'chat')

                if name and content:
                    template = Template(name=name, content=content, template_type=template_type)
                    db.add(template)
                    db.commit()

            elif action == 'edit':
                from datetime import datetime  # ⚠️ 放在函数最顶部只需导入一次
                template_id = request.form.get('id')
                name = request.form.get('name')
                content = request.form.get('content')
                template_type = request.form.get('template_type', 'chat')

                if template_id and name and content:
                    template = db.query(Template).filter(Template.id == template_id).first()
                    if template:
                        template.name = name
                        template.content = content
                        template.template_type = template_type
                        template.updated_at = datetime.utcnow()  # ✅ 加这行，确保缓存自动刷新
                        db.commit()


            elif action == 'delete':
                template_id = request.form.get('id')

                if template_id:
                    template = db.query(Template).filter(Template.id == template_id).first()
                    if template:
                        db.delete(template)
                        db.commit()

        templates = db.query(Template).all()
        return render_template('templates.html', templates=templates)
    finally:
        db.close()


@app.route('/user/ai_feeding', methods=['POST'])
def user_ai_feeding():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为 JSON 格式"}), 400

        username = data.get('username')
        content = data.get('content')
        feedback = data.get('feedback')

        if not username or not content:
            return jsonify({"error": "缺少必要参数"}), 400

        db = next(get_db())
        try:
            success = record_ai_feeding(db, username, content, feedback)
            if success:
                return jsonify({"message": "AI投喂成功"})
            else:
                return jsonify({"error": "AI投喂失败"}), 500
        finally:
            db.close()

    except Exception as e:
        import traceback
        logger.error(f"处理出错：{str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/user/billing', methods=['GET'])
def user_billing():
    try:
        username = request.args.get('username')
        user_id = request.args.get('user_id')

        if not username and not user_id:
            return jsonify({"error": "缺少用户名或用户ID参数"}), 400

        db = next(get_db())
        try:

            stats_service = StatisticsService(db)
            user_stats = stats_service.get_user_stats(user_id=user_id, username=username)
            if not user_stats:
                return jsonify({"error": "用户不存在"}), 404

            billing_records = db.query(BillingRecord).filter(
                BillingRecord.user_id == user_stats['id'] if 'id' in user_stats else 0
            ).order_by(BillingRecord.created_at.desc()).all()

            records = []
            for record in billing_records:
                records.append({
                    'id': record.id,
                    'tokens_used': record.tokens_used,
                    'duration_seconds': record.duration_seconds,
                    'cost': record.cost,
                    'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })

            return jsonify({
                'username': user_stats['username'],
                'user_id': user_stats['user_id'],
                'total_tokens': user_stats['total_tokens'],
                'total_duration': user_stats['total_duration'],
                'total_conversations': user_stats['total_conversations'],
                'active_days': user_stats['active_days'],
                'avg_response_time': user_stats['avg_response_time'],
                'token_balance': user_stats['token_balance'],
                'token_limit': user_stats['token_limit'],
                'token_package': user_stats['token_package'],
                'token_usage_labels': user_stats['token_usage_labels'],
                'token_usage_data': user_stats['token_usage_data'],
                'conversation_labels': user_stats['conversation_labels'],
                'conversation_data': user_stats['conversation_data'],
                'records': records
            })
        finally:
            db.close()

    except Exception as e:
        import traceback
        logger.error(f"处理出错：{str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/user/role', methods=['GET', 'POST'])
def user_role():
    try:
        db = next(get_db())
        from user_role import UserRoleManager
        role_manager = UserRoleManager(db)

        try:
            if request.method == 'GET':
                user_id = request.args.get('user_id')
                if not user_id:
                    return jsonify({"error": "缺少用户ID参数"}), 400

                role = role_manager.get_user_role(user_id)
                if not role:
                    return jsonify({"error": "用户未绑定角色"}), 404

                return jsonify(role)

            elif request.method == 'POST':
                data = request.get_json()
                if not data:
                    return jsonify({"error": "请求必须为 JSON 格式"}), 400

                user_id = data.get('user_id')
                template_name = data.get('template_name')
                username = data.get('username')

                if not user_id or not template_name:
                    return jsonify({"error": "缺少必要参数"}), 400

                success = role_manager.set_user_role(user_id, template_name, username)
                if not success:
                    return jsonify({"error": "设置角色失败"}), 500

                return jsonify({"message": "角色设置成功"})
        finally:
            db.close()

    except Exception as e:
        import traceback
        logger.error(f"处理出错：{str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/user/token_packages', methods=['GET'])
def user_token_packages():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return redirect(url_for('user_login'))

        packages = db.query(TokenPackage).filter(TokenPackage.is_active == True).all()

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template('user_token_packages.html',
                               user=user,
                               packages=packages,
                               message=message,
                               message_type=message_type)
    except Exception as e:
        logger.error(f"获取Token套餐出错: {str(e)}")
        return render_template('user_token_packages.html',
                               user=user,
                               packages=[],
                               message=f"获取套餐信息失败: {str(e)}",
                               message_type="danger")
    finally:
        db.close()


@app.route('/user/assign_package/<int:package_id>', methods=['GET'])
def user_assign_package(package_id):
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return redirect(url_for('user_login'))

        package = db.query(TokenPackage).filter(TokenPackage.id == package_id).first()
        if not package:
            return redirect(url_for('user_token_packages', message='套餐不存在', message_type='danger'))

        if not package.is_active:
            return redirect(url_for('user_token_packages', message='该套餐已停用', message_type='danger'))

        from database import TokenPackagePurchase, record_billing

        purchase = TokenPackagePurchase(
            user_id=user.id,
            package_id=package.id,
            purchase_time=datetime.now(),
            token_amount=package.token_amount,
            price=package.price,
            status='success'
        )
        db.add(purchase)

        previous_balance = user.token_balance
        user.token_balance += package.token_amount

        record_billing(db, user.user_id, tokens_used=0, duration_seconds=0,
                       template_name=f'购买套餐: {package.name}, 增加 {package.token_amount} Tokens')

        db.commit()

        return redirect(url_for('user_token_packages',
                                message=f'套餐购买成功！已增加 {package.token_amount} Tokens，当前余额: {user.token_balance}',
                                message_type='success'))
    except Exception as e:
        db.rollback()
        logger.error(f"购买套餐出错: {str(e)}")
        return redirect(url_for('user_token_packages', message=f'购买失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/template/<int:template_id>', methods=['GET'])
def get_template_by_id(template_id):
    if not session.get('admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = next(get_db())
    try:
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return jsonify({"error": "Template not found"}), 404

        return jsonify({
            "id": template.id,
            "name": template.name,
            "content": template.content,
            "template_type": getattr(template, 'template_type', 'chat')
        })
    finally:
        db.close()


@app.route('/admin/billing', methods=['GET'])
def admin_billing():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    time_range = request.args.get('time_range', 'month')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    db = next(get_db())
    try:

        stats_service = StatisticsService(db)
        stats = stats_service.get_billing_stats(time_range=time_range)

        query = db.query(BillingRecord).order_by(BillingRecord.created_at.desc())

        filter_date = None
        if time_range == 'today':
            filter_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'yesterday':
            filter_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        elif time_range == 'week':
            filter_date = datetime.utcnow() - timedelta(days=7)
        elif time_range == 'month':
            filter_date = datetime.utcnow() - timedelta(days=30)

        if filter_date:
            query = query.filter(BillingRecord.created_at >= filter_date)

        total_count = query.count()
        total_pages = (total_count + per_page - 1) // per_page

        records = query.offset((page - 1) * per_page).limit(per_page).all()

        billing_records = []
        for record in records:
            user = db.query(User).filter(User.id == record.user_id).first()
            billing_records.append({
                'id': record.id,
                'user_id': user.user_id if user else 'Unknown',
                'username': user.username if user else 'Unknown',
                'tokens_used': record.tokens_used,
                'duration_seconds': record.duration_seconds,
                'cost': record.cost,
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        token_usage_labels = [""] * 7
        token_usage_data = [0] * 7
        revenue_labels = [""] * 7
        revenue_data = [0] * 7

        time_range_text = ""
        if time_range == 'today':
            time_range_text = "今日"
        elif time_range == 'yesterday':
            time_range_text = "昨日"
        elif time_range == 'week':
            time_range_text = "本周"
        elif time_range == 'month':
            time_range_text = "本月"
        else:
            time_range_text = "全部"

        top_users = stats_service.get_top_users_by_token_usage(limit=10)

        total_users = db.query(User).count()
        total_tokens = db.query(func.sum(BillingRecord.tokens_used)).scalar() or 0
        total_conversations = db.query(func.count(BillingRecord.id)).scalar() or 0
        total_revenue = db.query(func.sum(TokenPackage.price)).scalar() or 0

        return render_template(
            'billing.html',
            stats=stats,
            billing_records=billing_records,
            page=page,
            total_pages=total_pages,
            time_range=time_range,
            per_page=per_page,
            token_usage_labels=decimal_json_dumps(token_usage_labels),
            token_usage_data=decimal_json_dumps(token_usage_data),
            revenue_labels=decimal_json_dumps(revenue_labels),
            revenue_data=decimal_json_dumps(revenue_data),
            time_range_text=time_range_text,
            top_users=top_users,
            total_users=total_users,
            total_tokens=total_tokens,
            total_conversations=total_conversations,
            total_revenue=total_revenue
        )
    finally:
        db.close()


@app.route('/admin/export_billing_data', methods=['GET'])
def admin_export_billing_data():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    time_range = request.args.get('time_range', 'month')
    search_term = request.args.get('search', '')

    db = next(get_db())
    try:
        filter_date = datetime.utcnow()
        if time_range == 'today':
            filter_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'yesterday':
            filter_date = (datetime.utcnow() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'week':
            filter_date = datetime.utcnow() - timedelta(days=7)
        elif time_range == 'month':
            filter_date = datetime.utcnow() - timedelta(days=30)

        query = db.query(BillingRecord)

        if time_range != 'all':
            query = query.filter(BillingRecord.created_at >= filter_date)

        if search_term:
            query = query.filter(
                BillingRecord.user_id.like(f'%{search_term}%')
            )

        records = query.order_by(BillingRecord.created_at.desc()).all()

        import io
        import csv
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)

        csv_writer.writerow(['ID', '用户ID', '用户名', 'Token消耗', '响应时间(秒)', '时间戳', '模板名称'])

        for record in records:
            user = db.query(User).filter(User.id == record.user_id).first()
            user_id = user.user_id if user else 'Unknown'
            username = user.username if user else 'Unknown'

            template_name = record.template_name if hasattr(record, 'template_name') else ''

            csv_writer.writerow([
                record.id,
                user_id,
                username,
                record.tokens_used,
                record.duration_seconds,
                record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                template_name
            ])

        response = make_response(csv_data.getvalue())
        response.headers[
            'Content-Disposition'] = f'attachment; filename=billing_data_{time_range}_{datetime.now().strftime("%Y%m%d")}.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'

        return response
    finally:
        db.close()


@app.route('/admin/token_packages', methods=['GET', 'POST'])
def admin_token_packages():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'add':
                name = request.form.get('name')
                description = request.form.get('description')
                token_amount = request.form.get('token_amount', type=int)
                price = request.form.get('price', type=float)
                is_active = request.form.get('is_active') == 'on'

                if name and description and token_amount and price:
                    package = TokenPackage(
                        name=name,
                        description=description,
                        token_amount=token_amount,
                        price=price,
                        is_active=is_active
                    )
                    db.add(package)
                    db.commit()
                    return redirect(url_for('admin_token_packages', message='套餐包添加成功', message_type='success'))
                else:
                    return render_template('token_packages.html', message='请填写所有必填字段', message_type='danger')

            elif action == 'edit':
                package_id = request.form.get('id', type=int)
                name = request.form.get('name')
                description = request.form.get('description')
                token_amount = request.form.get('token_amount', type=int)
                price = request.form.get('price', type=float)
                is_active = request.form.get('is_active') == 'on'

                if package_id and name and description and token_amount and price:
                    package = db.query(TokenPackage).filter(TokenPackage.id == package_id).first()
                    if package:
                        package.name = name
                        package.description = description
                        package.token_amount = token_amount
                        package.price = price
                        package.is_active = is_active
                        db.commit()
                        return redirect(
                            url_for('admin_token_packages', message='套餐包更新成功', message_type='success'))
                    else:
                        return render_template('token_packages.html', message='套餐包不存在', message_type='danger')
                else:
                    return render_template('token_packages.html', message='请填写所有必填字段', message_type='danger')

            elif action == 'delete':
                package_id = request.form.get('id', type=int)

                if package_id:
                    package = db.query(TokenPackage).filter(TokenPackage.id == package_id).first()
                    if package:
                        db.delete(package)
                        db.commit()
                        return redirect(
                            url_for('admin_token_packages', message='套餐包删除成功', message_type='success'))
                    else:
                        return render_template('token_packages.html', message='套餐包不存在', message_type='danger')
                else:
                    return render_template('token_packages.html', message='请提供套餐包ID', message_type='danger')

        stats_service = StatisticsService(db)
        package_stats = stats_service.get_token_package_stats()

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template(
            'token_packages.html',
            packages=package_stats['packages'],
            total_value=package_stats['total_value'],
            active_packages_count=package_stats['active_packages_count'],
            package_sales_labels=package_stats['package_sales_labels'],
            package_sales_data=package_stats['package_sales_data'],
            package_distribution_labels=package_stats['package_distribution_labels'],
            package_distribution_data=package_stats['package_distribution_data'],
            message=message,
            message_type=message_type
        )
    except Exception as e:
        logger.error(f"处理请求出错: {str(e)}")
        return redirect(url_for('user_dashboard', message='处理请求失败', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/token_package/<int:package_id>', methods=['GET'])
def get_token_package_by_id(package_id):
    if not session.get('admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = next(get_db())
    try:
        package = db.query(TokenPackage).filter(TokenPackage.id == package_id).first()
        if not package:
            return jsonify({"error": "Package not found"}), 404

        return jsonify({
            "id": package.id,
            "name": package.name,
            "description": package.description,
            "token_amount": package.token_amount,
            "price": package.price,
            "is_active": package.is_active
        })
    finally:
        db.close()


@app.route('/admin/token_package/toggle_status', methods=['POST'])
def toggle_token_package_status():
    if not session.get('admin'):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "请求必须为 JSON 格式"}), 400

    package_id = data.get('id')
    is_active = data.get('is_active')

    if package_id is None or is_active is None:
        return jsonify({"error": "缺少必要参数"}), 400

    db = next(get_db())
    try:
        package = db.query(TokenPackage).filter(TokenPackage.id == package_id).first()
        if not package:
            return jsonify({"error": "套餐包不存在"}), 404

        package.is_active = bool(is_active)
        db.commit()

        return jsonify({
            "success": True,
            "message": "套餐包状态已更新",
            "is_active": package.is_active
        })
    except Exception as e:
        db.rollback()
        return jsonify({
            "success": False,
            "message": f"更新失败: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route('/admin/user_chat_history', methods=['GET'])
def admin_user_chat_history():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    user_id = request.args.get('user_id')
    username = request.args.get('username')
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'all')
    search = request.args.get('search')

    if not user_id and not username:
        return redirect(url_for('admin_users', message='请指定用户ID或用户名', message_type='warning'))

    db = next(get_db())
    try:

        try:
            stats_service = StatisticsService(db)
            chat_history = stats_service.get_user_chat_history(
                user_id=user_id,
                username=username,
                page=page,
                filter_type=filter_type,
                search=search
            )

            if not chat_history:
                return redirect(url_for('admin_users', message='用户不存在或无聊天记录', message_type='warning'))

            total_pages = chat_history.get('total_pages', 1)

            print(f"Rendering template with total_pages={total_pages}, page={page}")

            template_vars = {
                'user_info': chat_history.get('user_info', {}),
                'conversations': chat_history.get('conversations', {}),
                'total_conversations': chat_history.get('total_conversations', 0),
                'total_tokens': chat_history.get('total_tokens', 0),
                'active_days': chat_history.get('active_days', 0),
                'avg_response_time': chat_history.get('avg_response_time', 0),
                'token_usage_labels': chat_history.get('token_usage_labels', []),
                'token_usage_data': chat_history.get('token_usage_data', []),
                'user_id': user_id or chat_history.get('user_info', {}).get('user_id', ''),
                'username': username or chat_history.get('user_info', {}).get('username', ''),
                'page': page,
                'total_pages': total_pages,  # 确保这个变量被传递
                'filter': filter_type,
                'search': search
            }

            return render_template('user_chat_history.html', **template_vars)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in admin_user_chat_history: {str(e)}\n{error_details}")
            return render_template(
                'error.html',
                message=f'获取聊天记录时出错: {str(e)}',
                details=error_details if session.get('admin') else None
            )
    finally:
        db.close()


@app.route('/admin/chat_history', methods=['GET'])
def admin_chat_history():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    user_id = request.args.get('user_id')
    filter_type = request.args.get('filter_type', 'all')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    if not user_id:
        return render_template('admin_chat_history.html')

    db = next(get_db())
    try:

        stats_service = StatisticsService(db)
        chat_history = stats_service.get_user_chat_history(
            user_id=user_id,
            page=page,
            per_page=per_page,
            filter_type=filter_type,
            search=search
        )

        if not chat_history:
            return render_template('admin_chat_history.html', error="未找到该用户")

        return render_template(
            'admin_chat_history.html',
            user_info=chat_history.get('user_info'),
            conversations=chat_history.get('conversations', {}),
            total_conversations=chat_history.get('total_conversations', 0),
            total_tokens=chat_history.get('total_tokens', 0),
            active_days=chat_history.get('active_days', 0),
            avg_response_time=chat_history.get('avg_response_time', 0),
            current_page=page,
            total_pages=chat_history.get('total_pages', 1),
            filter_type=filter_type
        )
    finally:
        db.close()


@app.route('/admin/industries', methods=['GET', 'POST'])
def admin_industries():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'add':
                name = request.form.get('name')
                description = request.form.get('description')

                if name:
                    industry = Industry(name=name, description=description)
                    db.add(industry)
                    db.commit()

            elif action == 'edit':
                industry_id = request.form.get('id')
                name = request.form.get('name')
                description = request.form.get('description')

                if industry_id and name:
                    industry = db.query(Industry).filter(Industry.id == industry_id).first()
                    if industry:
                        industry.name = name
                        industry.description = description
                        db.commit()

            elif action == 'delete':
                industry_id = request.form.get('id')

                if industry_id:
                    industry = db.query(Industry).filter(Industry.id == industry_id).first()
                    if industry:
                        db.delete(industry)
                        db.commit()

        industries = db.query(Industry).all()
        return render_template('industries.html', industries=industries)
    finally:
        db.close()


@app.route('/admin/intents', methods=['GET', 'POST'])
def admin_intents():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'add':
                industry_id = request.form.get('industry_id')
                name = request.form.get('name')
                description = request.form.get('description')
                api_endpoint = request.form.get('api_endpoint')
                parameters = request.form.get('parameters')

                if industry_id and name:
                    intent = Intent(
                        industry_id=industry_id,
                        name=name,
                        description=description,
                        api_endpoint=api_endpoint,
                        parameters=parameters
                    )
                    db.add(intent)
                    db.commit()

            elif action == 'edit':
                intent_id = request.form.get('id')
                industry_id = request.form.get('industry_id')
                name = request.form.get('name')
                description = request.form.get('description')
                api_endpoint = request.form.get('api_endpoint')
                parameters = request.form.get('parameters')

                if intent_id and industry_id and name:
                    intent = db.query(Intent).filter(Intent.id == intent_id).first()
                    if intent:
                        intent.industry_id = industry_id
                        intent.name = name
                        intent.description = description
                        intent.api_endpoint = api_endpoint
                        intent.parameters = parameters
                        db.commit()

            elif action == 'delete':
                intent_id = request.form.get('id')

                if intent_id:
                    intent = db.query(Intent).filter(Intent.id == intent_id).first()
                    if intent:
                        db.delete(intent)
                        db.commit()

        intents = db.query(Intent).all()
        industries = db.query(Industry).all()
        return render_template('intents.html', intents=intents, industries=industries)
    finally:
        db.close()


def initialize_database():
    create_tables()
    try:
        from database_migration import migrate_database
        migrate_database()
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")

    db = next(get_db())
    try:
        admin = db.query(User).filter(User.user_id == 'admin').first()
        if not admin:
            admin = User(user_id='admin', username='管理员', is_admin=True)
            db.add(admin)
            db.commit()
    finally:
        db.close()

    from config import CHAT_STORAGE_DIR, ENABLE_JSON_STORAGE
    if ENABLE_JSON_STORAGE:
        import os
        os.makedirs(CHAT_STORAGE_DIR, exist_ok=True)
        print(f"聊天记录存储目录已初始化: {CHAT_STORAGE_DIR}")


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.info(f"用户登录尝试: username={username}")

        if not username or not password:
            return render_template('user_login.html', error='请输入用户名和密码')

        db = next(get_db())
        try:
            user = db.query(User).filter(User.username == username).first()
            logger.info(f"按用户名查找用户: {user is not None}")

            if not user:
                user = db.query(User).filter(User.user_id == username).first()
                logger.info(f"按用户ID查找用户: {user is not None}")

            if user:
                logger.info(f"找到用户: {user.username}, 密码哈希: {user.password[:10] if user.password else 'None'}...")
                
                if user.user_id == password or username == password or user.password == password:
                    logger.info("简单密码验证成功")
                    session['user_id'] = user.user_id
                    session['username'] = user.username
                    session['user_id_str'] = user.user_id
                    session['user_logged_in'] = True
                    return redirect(url_for('user_dashboard'))

                import hashlib
                if user.password and password:
                    try:
                        password_hash = hashlib.md5(password.encode()).hexdigest()
                        logger.info(f"MD5验证: 输入密码哈希={password_hash[:10]}..., 存储密码哈希={user.password[:10] if user.password else 'None'}...")
                        if user.password == password_hash:
                            logger.info("MD5密码验证成功")
                            session['user_id'] = user.user_id
                            session['username'] = user.username
                            session['user_id_str'] = user.user_id
                            session['user_logged_in'] = True
                            return redirect(url_for('user_dashboard'))
                    except Exception as e:
                        logger.error(f"密码验证错误: {str(e)}")
            else:
                logger.info("未找到用户")

            return render_template('user_login.html', error='用户名或密码错误')
        except Exception as e:
            logger.error(f"登录过程中发生错误: {str(e)}")
            return render_template('user_login.html', error='登录系统错误，请稍后重试')
        finally:
            db.close()

    return render_template('user_login.html')


@app.route('/user/logout')
def user_logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('user_logged_in', None)
    return redirect(url_for('user_login'))


@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('user_login'))

        binding = db.query(UserTemplateBinding).filter(
            UserTemplateBinding.user_id == user.id
        ).order_by(UserTemplateBinding.updated_at.desc()).first()

        current_template = "未绑定"
        current_template_info = None

        if binding:
            template = db.query(Template).filter(Template.id == binding.template_id).first()
            if template:
                current_template = template.name

                industry_name = None
                if template.industry_id:
                    industry = db.query(Industry).filter(Industry.id == template.industry_id).first()
                    if industry:
                        industry_name = industry.name

                current_template_info = {
                    'name': template.name,
                    'industry_name': industry_name,
                    #'description': template.content[:100] + '...' if len(template.content) > 100 else template.content
                    'description': f"适用于{industry_name}行业的专业AI对话模板，帮助您更好地与客户互动" if industry_name else "通用场景AI对话模板，适用于各种客户互动场景"
                }

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_chat_count = db.query(ChatMessage).filter(
            ChatMessage.user_id == user.id,
            ChatMessage.created_at >= today_start
        ).count()

        recent_messages = []
        chat_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user.id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()

        for msg in reversed(chat_messages):
            recent_messages.append({
                'role': msg.role,
                'content': msg.content
            })

        package_info = None
        if user.token_package:
            package = db.query(TokenPackage).filter(TokenPackage.name == user.token_package).first()
            if package:
                package_info = {
                    'name': package.name,
                    'description': package.description,
                    'token_amount': package.token_amount
                }

        recent_activities = []

        billing_records = db.query(BillingRecord).filter(
            BillingRecord.user_id == user.id
        ).order_by(BillingRecord.created_at.desc()).limit(5).all()

        for record in billing_records:
            recent_activities.append({
                'icon': 'bi-chat-dots',
                'description': f'使用了 {record.template_name} 模板',
                'timestamp': record.created_at.strftime('%Y-%m-%d %H:%M'),
                'tokens': record.tokens_used
            })

        token_usage_data = {
            'labels': [],
            'values': []
        }

        for i in range(7):
            day = datetime.utcnow() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

            daily_tokens = db.query(func.sum(BillingRecord.tokens_used)).filter(
                BillingRecord.user_id == user.id,
                BillingRecord.created_at >= day_start,
                BillingRecord.created_at <= day_end
            ).scalar() or 0

            token_usage_data['labels'].insert(0, day.strftime('%m-%d'))
            token_usage_data['values'].insert(0, daily_tokens)

        return render_template(
            'user_dashboard.html',
            user=user,
            current_template=current_template,
            current_template_info=current_template_info,
            today_chat_count=today_chat_count,
            recent_messages=recent_messages,
            package_info=package_info,
            recent_activities=recent_activities,
            token_usage_data=decimal_json_dumps(token_usage_data),
            token_usage_labels=decimal_json_dumps(token_usage_data['labels']),
            token_usage_values=decimal_json_dumps(token_usage_data['values'])
        )
    finally:
        db.close()


@app.route('/user/stats')
def user_stats():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_chat_count = db.query(ChatMessage).filter(
            ChatMessage.user_id == user.id,
            ChatMessage.created_at >= today_start
        ).count()

        token_usage_data = {
            'labels': [],
            'values': []
        }

        for i in range(7):
            day = datetime.utcnow() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

            daily_tokens = db.query(func.sum(BillingRecord.tokens_used)).filter(
                BillingRecord.user_id == user.id,
                BillingRecord.created_at >= day_start,
                BillingRecord.created_at <= day_end
            ).scalar() or 0

            token_usage_data['labels'].insert(0, day.strftime('%m-%d'))
            token_usage_data['values'].insert(0, daily_tokens)

        return jsonify({
            'token_balance': user.token_balance,
            'today_chat_count': today_chat_count,
            'token_usage_data': token_usage_data
        })
    finally:
        db.close()


@app.route('/user/profile')
def user_profile():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('user_login'))

        profile_data = {}
        if user.profile_data:
            try:
                profile_data = json.loads(user.profile_data)
            except:
                profile_data = {}

        return render_template(
            'user_profile.html',
            user=user,
            profile_data=profile_data
        )
    finally:
        db.close()


@app.route('/user/templates')
def user_templates():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('user_login'))

        templates = db.query(Template).all()

        binding = db.query(UserTemplateBinding).filter(
            UserTemplateBinding.user_id == user.id
        ).order_by(UserTemplateBinding.updated_at.desc()).first()

        current_template_id = None
        if binding:
            current_template_id = binding.template_id

        industries = db.query(Industry).all()

        return render_template(
            'user_templates.html',
            user=user,
            templates=templates,
            current_template_id=current_template_id,
            industries=industries
        )
    finally:
        db.close()


@app.route('/user/bind_template', methods=['POST'])
def user_bind_template():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    template_id = request.form.get('template_id')
    if not template_id:
        return jsonify({'error': '缺少模板ID'}), 400

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return jsonify({'error': '模板不存在'}), 404

        binding = db.query(UserTemplateBinding).filter(
            UserTemplateBinding.user_id == user.id
        ).first()

        if binding:
            binding.template_id = template.id
            binding.updated_at = datetime.utcnow()
        else:
            binding = UserTemplateBinding(
                user_id=user.id,
                template_id=template.id
            )
            db.add(binding)

        db.commit()

        return jsonify({'success': True, 'message': f'成功绑定模板: {template.name}'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'绑定模板失败: {str(e)}'}), 500
    finally:
        db.close()


@app.route('/user/chat_history')
def user_chat_history():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    page = request.args.get('page', 1, type=int)
    per_page = 20

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('user_login'))

        total_messages = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.user_id == user.id
        ).scalar()

        total_pages = (total_messages + per_page - 1) // per_page

        messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user.id
        ).order_by(ChatMessage.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        grouped_messages = {}
        for message in messages:
            date_str = message.created_at.strftime('%Y-%m-%d')
            if date_str not in grouped_messages:
                grouped_messages[date_str] = []

            grouped_messages[date_str].append({
                'id': message.id,
                'content': message.content,
                'is_from_user': message.role == 'user' if hasattr(message, 'role') else (
                    message.sender_type == 'user' if hasattr(message, 'sender_type') else False),
                'time': message.created_at.strftime('%H:%M:%S')
            })

        sorted_dates = sorted(grouped_messages.keys(), reverse=True)

        return render_template(
            'user_chat_history.html',
            user=user,
            grouped_messages=grouped_messages,
            dates=sorted_dates,
            page=page,
            total_pages=total_pages
        )
    finally:
        db.close()


@app.route('/admin/settings', methods=['GET'])
def admin_settings():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        from config import (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL, MAX_TOKEN, TEMPERATURE,
                            MAX_CONTEXT_LENGTH, RATE_LIMIT_PER_MINUTE, ENABLE_JSON_STORAGE,
                            CHAT_STORAGE_DIR, MAX_CONTEXT_MESSAGES, SYNC_DB_WITH_JSON,
                            CHAT_ACTIVE_MINUTES, GREETING_CONTEXT_MESSAGES, AUTO_MESSAGE,
                            ENABLE_AUTO_MESSAGE, MIN_COUNTDOWN_HOURS, MAX_COUNTDOWN_HOURS,
                            NOON_QUIET_TIME_START, NOON_QUIET_TIME_END,
                            EVENING_QUIET_TIME_START, EVENING_QUIET_TIME_END,
                            USER_RATE_LIMIT_PER_MINUTE, MAX_DAILY_REQUESTS_PER_USER,
                            MAX_REQUEST_SIZE, ENABLE_USER_SPECIFIC_LIMITS,
                            MAX_CONNECTION_TIME, CONNECTION_TIMEOUT)

        system_settings = {
            'DEEPSEEK_API_KEY': DEEPSEEK_API_KEY,
            'DEEPSEEK_API_URL': DEEPSEEK_BASE_URL,
            'DEEPSEEK_MODEL': MODEL,
            'MAX_TOKENS': MAX_TOKEN,
            'TEMPERATURE': TEMPERATURE,
            'MAX_CONTEXT_LENGTH': MAX_CONTEXT_LENGTH,
            'RATE_LIMIT_PER_MINUTE': RATE_LIMIT_PER_MINUTE,
            'USER_RATE_LIMIT_PER_MINUTE': USER_RATE_LIMIT_PER_MINUTE,
            'MAX_DAILY_REQUESTS_PER_USER': MAX_DAILY_REQUESTS_PER_USER,
            'MAX_REQUEST_SIZE': MAX_REQUEST_SIZE,
            'ENABLE_USER_SPECIFIC_LIMITS': ENABLE_USER_SPECIFIC_LIMITS,
            'MAX_CONNECTION_TIME': MAX_CONNECTION_TIME,
            'CONNECTION_TIMEOUT': CONNECTION_TIMEOUT
        }

        chat_settings = {
            'ENABLE_JSON_STORAGE': ENABLE_JSON_STORAGE,
            'CHAT_STORAGE_DIR': CHAT_STORAGE_DIR,
            'MAX_CONTEXT_MESSAGES': MAX_CONTEXT_MESSAGES,
            'SYNC_DB_WITH_JSON': SYNC_DB_WITH_JSON,
            'CHAT_ACTIVE_MINUTES': CHAT_ACTIVE_MINUTES,
            'GREETING_CONTEXT_MESSAGES': GREETING_CONTEXT_MESSAGES
        }

        greeting_settings = {
            'AUTO_MESSAGE': AUTO_MESSAGE,
            'ENABLE_AUTO_MESSAGE': ENABLE_AUTO_MESSAGE,
            'MIN_COUNTDOWN_HOURS': MIN_COUNTDOWN_HOURS,
            'MAX_COUNTDOWN_HOURS': MAX_COUNTDOWN_HOURS,
            'NOON_QUIET_TIME_START': NOON_QUIET_TIME_START,
            'NOON_QUIET_TIME_END': NOON_QUIET_TIME_END,
            'EVENING_QUIET_TIME_START': EVENING_QUIET_TIME_START,
            'EVENING_QUIET_TIME_END': EVENING_QUIET_TIME_END
        }

        from config import IP_WHITELIST, IP_BLACKLIST

        ip_whitelist = IP_WHITELIST
        ip_blacklist = IP_BLACKLIST

        admin = {
            'username': 'admin'
        }

        user_count = db.query(User).count()
        template_count = db.query(Template).count()
        db_status = True  # 数据库连接状态

        api_status = True  # API连接状态
        stats_service = StatisticsService(db)
        today_api_calls = stats_service.get_api_calls_count(period='today')
        month_api_calls = stats_service.get_api_calls_count(period='month')
        month_token_usage = stats_service.get_token_usage(period='month')

        resource_timestamps = json.dumps([f"{i}:00" for i in range(24)])
        cpu_usage = json.dumps([round(30 + 10 * (i % 5)) for i in range(24)])
        memory_usage = json.dumps([round(40 + 5 * (i % 7)) for i in range(24)])
        disk_usage = json.dumps([round(50 + 2 * (i % 3)) for i in range(24)])

        return render_template(
            'settings.html',
            settings=system_settings,
            chat_settings=chat_settings,
            greeting_settings=greeting_settings,
            ip_whitelist=ip_whitelist,
            ip_blacklist=ip_blacklist,
            admin=admin,
            message=message,
            message_type=message_type,
            user_count=user_count,
            template_count=template_count,
            db_status=db_status,
            api_status=api_status,
            today_api_calls=today_api_calls,
            month_api_calls=month_api_calls,
            month_token_usage=month_token_usage,
            resource_timestamps=resource_timestamps,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage
        )
    finally:
        db.close()


@app.route('/admin/edit_user', methods=['POST'])
def admin_edit_user():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        user_id = request.form.get('user_id')
        username = request.form.get('username')
        token_balance = request.form.get('token_balance', type=int)
        token_limit = request.form.get('token_limit', type=int)
        template = request.form.get('template')
        has_appointment = 'has_appointment' in request.form
        identity = request.form.get('identity', '')
        hobbies = request.form.get('hobbies', '')
        
        real_name = request.form.get('real_name', '')
        id_number = request.form.get('id_number', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')

        if user_id and username:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.username = username
                user.token_balance = token_balance
                user.token_limit = token_limit
                user.has_appointment = has_appointment
                user.identity = identity
                user.hobbies = hobbies
                
                user.real_name = real_name
                user.id_number = id_number
                user.phone = phone
                user.email = email

                if template:
                    bind_template_to_db(db, user.user_id, template, username)

                db.commit()
                return redirect(url_for('admin_users', message='用户更新成功', message_type='success'))

        return redirect(url_for('admin_users', message='用户更新失败', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/user/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    if not session.get('admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = next(get_db())
    try:
        if user_id.isdigit():
            user = db.query(User).filter((User.id == int(user_id)) | (User.user_id == user_id)).first()
        else:
            user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            user = db.query(User).filter(User.username == user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        template_name = get_bound_template_from_db(db, user.user_id)

        return jsonify({
            "id": user.id,
            "user_id": user.user_id,
            "username": user.username,
            "token_balance": user.token_balance,
            "token_limit": user.token_limit,
            "template": template_name,
            "has_appointment": user.has_appointment,
            "identity": user.identity,
            "hobbies": user.hobbies
        })
    finally:
        db.close()


@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    user_id = request.form.get('user_id')
    username = request.form.get('username')
    token_balance = request.form.get('token_balance', type=int)
    token_limit = request.form.get('token_limit', type=int)
    template = request.form.get('template')
    has_appointment = 'has_appointment' in request.form
    identity = request.form.get('identity', '')
    hobbies = request.form.get('hobbies', '')
    
    real_name = request.form.get('real_name', '')
    id_number = request.form.get('id_number', '')
    phone = request.form.get('phone', '')
    email = request.form.get('email', '')

    db = next(get_db())
    try:
        existing = db.query(User).filter(User.user_id == user_id).first()
        if existing:
            return redirect(url_for('admin_users', message=f'用户ID "{user_id}" 已存在', message_type='danger'))

        new_user = User(
            user_id=user_id,
            username=username,
            token_balance=token_balance,
            token_limit=token_limit,
            has_appointment=has_appointment,
            identity=identity,
            hobbies=hobbies,
            real_name=real_name,
            id_number=id_number,
            phone=phone,
            email=email
        )
        db.add(new_user)
        db.commit()

        if template:
            template_obj = db.query(Template).filter(Template.name == template).first()
            if template_obj:
                bind_template_to_db(db, user_id, template, username)

        return redirect(url_for('admin_users', message=f'用户 "{username}" 添加成功', message_type='success'))
    except Exception as e:
        db.rollback()
        return redirect(url_for('admin_users', message=f'添加用户失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/recharge_user', methods=['POST'])
def admin_recharge_user():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    user_id = request.form.get('user_id')
    amount = request.form.get('amount', type=int)
    package = request.form.get('package')
    note = request.form.get('note', '')

    if not user_id or not amount or amount <= 0:
        return redirect(url_for('admin_users', message='充值数量必须大于0', message_type='danger'))

    db = next(get_db())
    try:
        user_query = db.query(User)
        if user_id.isdigit():
            user = user_query.filter((User.id == int(user_id)) | (User.user_id == user_id)).first()
        else:
            user = user_query.filter(User.user_id == user_id).first()

        if not user:
            user = db.query(User).filter(User.username == user_id).first()

        if not user:
            return redirect(url_for('admin_users', message='用户不存在', message_type='danger'))

        previous_balance = user.token_balance
        user.token_balance += amount

        template_name = f'充值: 管理员充值 {amount} Tokens'
        if note:
            template_name += f', {note}'

        record_billing(db, user.id, tokens_used=0, duration_seconds=0, template_name=template_name)

        db.commit()

        return redirect(
            url_for('admin_users', message=f'用户充值成功，已添加 {amount} Tokens，当前余额: {user.token_balance}',
                    message_type='success'))
    except Exception as e:
        db.rollback()
        return redirect(url_for('admin_users', message=f'充值失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/add_token_package', methods=['POST'])
def admin_add_token_package():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    name = request.form.get('name')
    description = request.form.get('description')
    token_amount = request.form.get('token_amount')
    price = request.form.get('price')
    is_active = request.form.get('is_active') == 'on'

    if not name or not description or not token_amount or not price:
        return redirect(url_for('admin_token_packages', message='所有字段都是必填的', message_type='danger'))

    db = next(get_db())
    try:
        existing = db.query(TokenPackage).filter(TokenPackage.name == name).first()
        if existing:
            return redirect(url_for('admin_token_packages', message=f'套餐包 "{name}" 已存在', message_type='danger'))

        package = TokenPackage(
            name=name,
            description=description,
            token_amount=int(token_amount),
            price=float(price),
            is_active=is_active
        )
        db.add(package)
        db.commit()

        return redirect(url_for('admin_token_packages', message=f'套餐包 "{name}" 添加成功', message_type='success'))
    except Exception as e:
        db.rollback()
        return redirect(url_for('admin_token_packages', message=f'添加套餐包失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/edit_token_package', methods=['POST'])
def admin_edit_token_package():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    package_id = request.form.get('id')
    name = request.form.get('name')
    description = request.form.get('description')
    token_amount = request.form.get('token_amount')
    price = request.form.get('price')

    if not package_id or not name or not description or not token_amount or not price:
        return redirect(url_for('admin_token_packages', message='所有字段都是必填的', message_type='danger'))

    db = next(get_db())
    try:
        package = db.query(TokenPackage).filter(TokenPackage.id == package_id).first()
        if not package:
            return redirect(url_for('admin_token_packages', message='套餐包不存在', message_type='danger'))

        package.name = name
        package.description = description
        package.token_amount = int(token_amount)
        package.price = float(price)
        db.commit()

        return redirect(url_for('admin_token_packages', message=f'套餐包 "{name}" 更新成功', message_type='success'))
    except Exception as e:
        db.rollback()
        return redirect(url_for('admin_token_packages', message=f'更新套餐包失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/delete_token_package', methods=['POST'])
def admin_delete_token_package():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    package_id = request.form.get('id')

    if not package_id:
        return redirect(url_for('admin_token_packages', message='请提供套餐包ID', message_type='danger'))

    db = next(get_db())
    try:
        package = db.query(TokenPackage).filter(TokenPackage.id == package_id).first()
        if not package:
            return redirect(url_for('admin_token_packages', message='套餐包不存在', message_type='danger'))

        users_with_package = db.query(User).filter(User.token_package == package.name).count()
        if users_with_package > 0:
            return redirect(url_for('admin_token_packages',
                                    message=f'无法删除套餐包：有 {users_with_package} 个用户正在使用此套餐包',
                                    message_type='warning'))

        package_name = package.name
        db.delete(package)
        db.commit()

        return redirect(url_for('admin_token_packages',
                                message=f'套餐包 "{package_name}" 已成功删除',
                                message_type='success'))
    except Exception as e:
        db.rollback()
        return redirect(url_for('admin_token_packages',
                                message=f'删除套餐包失败: {str(e)}',
                                message_type='danger'))
    finally:
        db.close()


@app.route('/admin/update_api_settings', methods=['POST'])
def admin_update_api_settings():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        deepseek_api_key = request.form.get('deepseek_api_key')
        deepseek_api_url = request.form.get('deepseek_api_url')
        deepseek_model = request.form.get('deepseek_model')

        from config import update_config
        update_config('DEEPSEEK_API_KEY', deepseek_api_key)
        update_config('DEEPSEEK_BASE_URL', deepseek_api_url)
        update_config('MODEL', deepseek_model)

        return redirect(url_for('admin_settings', message='API设置已更新', message_type='success'))
    except Exception as e:
        return redirect(url_for('admin_settings', message=f'更新API设置失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/update_ai_settings', methods=['POST'])
def admin_update_ai_settings():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        max_tokens = request.form.get('max_tokens', type=int, default=1024)
        temperature = request.form.get('temperature', type=float, default=0.7)
        max_context_length = request.form.get('max_context_length', type=int, default=50)

        from config import update_config
        update_config('MAX_TOKEN', max_tokens)
        update_config('TEMPERATURE', temperature)
        update_config('MAX_CONTEXT_LENGTH', max_context_length)

        return redirect(url_for('admin_settings', message='AI设置已更新', message_type='success'))
    except Exception as e:
        return redirect(url_for('admin_settings', message=f'更新AI设置失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/update_security_settings', methods=['POST'])
def admin_update_security_settings():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        rate_limit = request.form.get('rate_limit', type=int, default=60)
        user_rate_limit = request.form.get('user_rate_limit', type=int, default=60)
        max_daily_requests = request.form.get('max_daily_requests', type=int, default=1000)
        max_request_size = request.form.get('max_request_size', type=int, default=4096)
        max_connection_time = request.form.get('max_connection_time', type=int, default=30)
        connection_timeout = request.form.get('connection_timeout', type=int, default=60)
        enable_user_specific_limits = 'enable_user_specific_limits' in request.form

        ip_whitelist = request.form.get('ip_whitelist', '')
        ip_blacklist = request.form.get('ip_blacklist', '')

        whitelist = [ip.strip() for ip in ip_whitelist.split('\n') if ip.strip()]
        blacklist = [ip.strip() for ip in ip_blacklist.split('\n') if ip.strip()]

        from config import update_config
        update_config('RATE_LIMIT_PER_MINUTE', rate_limit)
        update_config('USER_RATE_LIMIT_PER_MINUTE', user_rate_limit)
        update_config('MAX_DAILY_REQUESTS_PER_USER', max_daily_requests)
        update_config('MAX_REQUEST_SIZE', max_request_size)
        update_config('ENABLE_USER_SPECIFIC_LIMITS', enable_user_specific_limits)
        update_config('MAX_CONNECTION_TIME', max_connection_time)
        update_config('CONNECTION_TIMEOUT', connection_timeout)
        update_config('IP_WHITELIST', whitelist)
        update_config('IP_BLACKLIST', blacklist)

        return redirect(url_for('admin_settings', message='安全设置已更新', message_type='success'))
    except Exception as e:
        return redirect(url_for('admin_settings', message=f'更新安全设置失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/update_admin_settings', methods=['POST'])
def admin_update_admin_settings():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        admin_username = request.form.get('admin_username')
        admin_password = request.form.get('admin_password')
        admin_password_confirm = request.form.get('admin_password_confirm')

        if admin_password and admin_password != admin_password_confirm:
            return redirect(url_for('admin_settings', message='两次输入的密码不一致', message_type='danger'))

        from config import update_config
        update_config('ADMIN_USERNAME', admin_username)
        if admin_password:
            update_config('ADMIN_PASSWORD', admin_password)

        return redirect(url_for('admin_settings', message='管理员设置已更新', message_type='success'))
    except Exception as e:
        return redirect(url_for('admin_settings', message=f'更新管理员设置失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/update_chat_settings', methods=['POST'])
def admin_update_chat_settings():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        enable_json_storage = 'enable_json_storage' in request.form
        chat_storage_dir = request.form.get('chat_storage_dir', 'chat_records')
        max_context_messages = request.form.get('max_context_messages', type=int, default=10)
        sync_db_with_json = 'sync_db_with_json' in request.form

        chat_active_minutes = request.form.get('chat_active_minutes', type=int, default=30)
        greeting_context_messages = request.form.get('greeting_context_messages', type=int, default=5)

        from config import update_config
        update_config('ENABLE_JSON_STORAGE', enable_json_storage)
        update_config('CHAT_STORAGE_DIR', chat_storage_dir)
        update_config('MAX_CONTEXT_MESSAGES', max_context_messages)
        update_config('SYNC_DB_WITH_JSON', sync_db_with_json)
        update_config('CHAT_ACTIVE_MINUTES', chat_active_minutes)
        update_config('GREETING_CONTEXT_MESSAGES', greeting_context_messages)

        if enable_json_storage:
            import os
            os.makedirs(chat_storage_dir, exist_ok=True)

        return redirect(url_for('admin_settings', message='聊天记录设置已更新', message_type='success'))
    except Exception as e:
        return redirect(url_for('admin_settings', message=f'更新聊天记录设置失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/update_greeting_settings', methods=['POST'])
def admin_update_greeting_settings():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        auto_message = request.form.get('auto_message', '请你模拟系统设置的角色，在微信上找对方发消息想知道对方在做什么')
        enable_auto_message = 'enable_auto_message' in request.form
        min_countdown_hours = request.form.get('min_countdown_hours', type=float, default=1)
        max_countdown_hours = request.form.get('max_countdown_hours', type=float, default=2)

        noon_quiet_time_start = request.form.get('noon_quiet_time_start', '11:30')
        noon_quiet_time_end = request.form.get('noon_quiet_time_end', '13:30')

        evening_quiet_time_start = request.form.get('evening_quiet_time_start', '22:00')
        evening_quiet_time_end = request.form.get('evening_quiet_time_end', '07:00')

        from config import update_config
        update_config('AUTO_MESSAGE', auto_message)
        update_config('ENABLE_AUTO_MESSAGE', enable_auto_message)
        update_config('MIN_COUNTDOWN_HOURS', min_countdown_hours)
        update_config('MAX_COUNTDOWN_HOURS', max_countdown_hours)

        update_config('NOON_QUIET_TIME_START', noon_quiet_time_start)
        update_config('NOON_QUIET_TIME_END', noon_quiet_time_end)

        update_config('EVENING_QUIET_TIME_START', evening_quiet_time_start)
        update_config('EVENING_QUIET_TIME_END', evening_quiet_time_end)

        return redirect(url_for('admin_settings', message='问候设置已更新', message_type='success'))
    except Exception as e:
        logger.error(f"更新问候设置出错: {str(e)}")
        return redirect(url_for('admin_settings', message=f'更新问候设置失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/personalized_prompt', methods=['GET'])
def admin_personalized_prompt():
    """个性化提示词设置页面"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        from config import ENABLE_PERSONALIZED_PROMPT, PERSONALIZED_PROMPT_TEMPLATE, CUSTOM_PLACEHOLDERS

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template(
            'admin_personalized_prompt.html',
            ENABLE_PERSONALIZED_PROMPT=ENABLE_PERSONALIZED_PROMPT,
            PERSONALIZED_PROMPT_TEMPLATE=PERSONALIZED_PROMPT_TEMPLATE,
            CUSTOM_PLACEHOLDERS=CUSTOM_PLACEHOLDERS,
            message=message,
            message_type=message_type
        )
    except Exception as e:
        logger.error(f"加载个性化提示词设置出错: {str(e)}")
        return render_template('admin_personalized_prompt.html', message=f"加载设置出错: {str(e)}",
                               message_type="danger")
    finally:
        db.close()


@app.route('/admin/update_personalized_prompt_settings', methods=['POST'])
def admin_update_personalized_prompt_settings():
    """更新个性化提示词设置"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        enable_personalized_prompt = 'enable_personalized_prompt' in request.form
        personalized_prompt_template = request.form.get('personalized_prompt_template', '')

        from config import update_config
        update_config('ENABLE_PERSONALIZED_PROMPT', enable_personalized_prompt)

        if personalized_prompt_template:
            update_config('PERSONALIZED_PROMPT_TEMPLATE', personalized_prompt_template)

        custom_placeholders = request.form.get('custom_placeholders', '')
        if custom_placeholders:
            update_config('CUSTOM_PLACEHOLDERS', custom_placeholders)

        return redirect(url_for('admin_personalized_prompt', message='个性化提示词设置已更新', message_type='success'))
    except Exception as e:
        logger.error(f"更新个性化提示词设置出错: {str(e)}")
        return redirect(
            url_for('admin_personalized_prompt', message=f'更新个性化提示词设置失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/admin/ai_profiling', methods=['GET'])
def admin_ai_profiling():
    """朋友圈AI画像分析设置页面"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    try:
        db = next(get_db())
        ai_strategy = db.query(AIStrategy).filter_by(name="朋友圈画像分析").first()
        
        if not ai_strategy:
            ai_strategy = AIStrategy(
                name="朋友圈画像分析",
                description="用于分析微信朋友圈内容生成用户画像",
                prompt_template="""请分析以下微信朋友圈内容，生成用户画像：

朋友圈内容：
{moments_content}

请根据以上内容分析用户特征，并以JSON格式返回：
{
  "summary": "用户画像摘要描述",
  "labels": ["标签1", "标签2", "标签3"],
  "category": "客户分组归类（高价值客户/中价值客户/普通客户/潜力客户）",
  "hobbies": ["兴趣爱好1", "兴趣爱好2", "兴趣爱好3"]
}""",
                system_message="你是专业的用户画像分析师，请根据用户的朋友圈内容分析其特征和兴趣。",
                temperature=0.7,
                max_tokens=2000
            )
            db.add(ai_strategy)
            db.commit()

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template(
            'admin_ai_profiling.html',
            profiling_prompt_template=ai_strategy.prompt_template,
            system_message=ai_strategy.system_message,
            temperature=ai_strategy.temperature,
            max_tokens=ai_strategy.max_tokens,
            message=message,
            message_type=message_type
        )
    except Exception as e:
        logger.error(f"加载朋友圈AI画像设置出错: {str(e)}")
        return render_template('admin_ai_profiling.html', message=f"加载设置出错: {str(e)}",
                               message_type="danger")
    finally:
        if 'db' in locals():
            db.close()


@app.route('/admin/update_ai_profiling_settings', methods=['POST'])
def admin_update_ai_profiling_settings():
    """更新朋友圈AI画像分析设置"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    try:
        db = next(get_db())
        profiling_prompt_template = request.form.get('profiling_prompt_template', '')
        system_message = request.form.get('system_message', '')
        temperature = float(request.form.get('temperature', 0.7))
        max_tokens = int(request.form.get('max_tokens', 2000))

        ai_strategy = db.query(AIStrategy).filter_by(name="朋友圈画像分析").first()
        if not ai_strategy:
            ai_strategy = AIStrategy(
                name="朋友圈画像分析",
                description="用于分析微信朋友圈内容生成用户画像"
            )
            db.add(ai_strategy)

        ai_strategy.prompt_template = profiling_prompt_template
        ai_strategy.system_message = system_message
        ai_strategy.temperature = temperature
        ai_strategy.max_tokens = max_tokens
        ai_strategy.updated_at = datetime.utcnow()

        db.commit()

        return redirect(url_for('admin_ai_profiling', message='朋友圈AI画像设置已更新', message_type='success'))
    except Exception as e:
        logger.error(f"更新朋友圈AI画像设置出错: {str(e)}")
        return redirect(
            url_for('admin_ai_profiling', message=f'更新设置失败: {str(e)}', message_type='danger'))
    finally:
        if 'db' in locals():
            db.close()


@app.route('/api/user_profile', methods=['POST'])
def update_user_profile():
    """更新用户资料API，允许直接更新用户身份和爱好信息"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        identity = data.get("identity")
        hobbies = data.get("hobbies")

        if not user_id:
            return jsonify({"error": "缺少必要参数: user_id"}), 400

        db = next(get_db())
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return jsonify({"error": "用户不存在"}), 404

            if identity is not None:
                user.identity = identity
            if hobbies is not None:
                user.hobbies = hobbies

            db.commit()
            return jsonify({"success": True, "message": "用户资料已更新"})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/greeting', methods=['POST'])
def get_greeting():
    """获取用户问候API
    当用户不在聊天状态时，返回AI生成的问候语；当用户在聊天状态时，返回空响应
    问候语基于用户的历史上下文和模板，直接从数据库读取
    """
    try:
        data = request.get_json()
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"error": "缺少必要参数: user_id"}), 400

        db = next(get_db())
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return jsonify({"error": "用户不存在"}), 404

            from config import CHAT_ACTIVE_MINUTES, GREETING_CONTEXT_MESSAGES, ENABLE_AUTO_MESSAGE

            active_time_ago = datetime.utcnow() - timedelta(minutes=CHAT_ACTIVE_MINUTES)

            recent_messages = db.query(ChatMessage).filter(
                ChatMessage.user_id == user.id,
                ChatMessage.created_at >= active_time_ago
            ).limit(GREETING_CONTEXT_MESSAGES).all()

            if recent_messages and len(recent_messages) > 0:
                return jsonify({"greeting": "", "in_chat": True})

            if not ENABLE_AUTO_MESSAGE:
                return jsonify({"greeting": "", "in_chat": False})

            from config import (NOON_QUIET_TIME_START, NOON_QUIET_TIME_END,
                                EVENING_QUIET_TIME_START, EVENING_QUIET_TIME_END)

            current_time = datetime.now().time()

            noon_start = datetime.strptime(NOON_QUIET_TIME_START, '%H:%M').time()
            noon_end = datetime.strptime(NOON_QUIET_TIME_END, '%H:%M').time()
            evening_start = datetime.strptime(EVENING_QUIET_TIME_START, '%H:%M').time()
            evening_end = datetime.strptime(EVENING_QUIET_TIME_END, '%H:%M').time()

            in_noon_quiet_time = noon_start <= current_time <= noon_end

            if evening_start <= evening_end:  # 不跨午夜
                in_evening_quiet_time = evening_start <= current_time <= evening_end
            else:  # 跨午夜
                in_evening_quiet_time = current_time >= evening_start or current_time <= evening_end

            if in_noon_quiet_time or in_evening_quiet_time:
                return jsonify({"greeting": "", "in_chat": False, "in_quiet_time": True})

            binding = db.query(UserTemplateBinding).filter(
                UserTemplateBinding.user_id == user.id
            ).order_by(UserTemplateBinding.updated_at.desc()).first()

            if not binding:
                logger.error(f"获取问候语出错: 用户未绑定模板 | 用户ID: {user_id} | 用户名: {user.username}")
                return jsonify({"error": "用户未绑定模板"}), 400

            template = db.query(Template).filter(Template.id == binding.template_id).first()
            if not template:
                return jsonify({"error": f"模板不存在: ID={binding.template_id}"}), 400

            from config import GREETING_CONTEXT_MESSAGES
            context_messages_limit = GREETING_CONTEXT_MESSAGES if 'GREETING_CONTEXT_MESSAGES' in globals() else 10

            context = db.query(Context).filter(
                Context.user_id == user.id,
                Context.template_id == template.id
            ).order_by(Context.updated_at.desc()).first()

            context_data = []
            if context:
                messages = db.query(ChatMessage).filter(
                    ChatMessage.context_id == context.id
                ).order_by(ChatMessage.created_at.desc()).limit(context_messages_limit).all()

                messages.reverse()

                for msg in messages:
                    context_data.append({
                        "role": "user" if msg.is_from_user else "assistant",
                        "content": msg.content
                    })

            from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL, MAX_TOKEN, TEMPERATURE

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

            template_content = template.content

            greeting_prompt = f"{template_content}\n\n请根据用户的资料和历史对话，生成一条自然、友好的问候语，询问用户最近在做什么。确保问候语符合用户的身份和关系背景。"

            context_data.append({"role": "user", "content": "请给我发一条问候语"})

            try:
                response = ai_service.client.chat.create(
                    model=ai_service.model,
                    messages=[{"role": "system", "content": greeting_prompt}] + context_data,
                    temperature=ai_service.temperature,
                    max_tokens=ai_service.max_tokens
                )

                result = response.model_dump()
                if "choices" in result and result["choices"]:
                    content = result["choices"][0]["message"]["content"]
                    greeting, confidence, intent_data = ai_service.extract_reply_and_confidence(content)

                    tokens_used = result.get("usage", {}).get("total_tokens", 0)
                    if user:
                        user.token_balance = max(0, user.token_balance - tokens_used)
                        db.commit()

                    try:
                        from database import record_billing
                        record_billing(db, user.id, tokens_used, 0, template.name)
                    except Exception as billing_error:
                        logger.error(f"记录账单出错: {str(billing_error)}")

                    return jsonify({"greeting": greeting, "in_chat": False, "in_quiet_time": False})
                else:
                    logger.error("AI响应无效")
                    return jsonify({"greeting": "你好，最近在做什么呢？", "in_chat": False, "in_quiet_time": False})

            except Exception as e:
                logger.error(f"生成问候语出错: {str(e)}")
                return jsonify({"greeting": "你好，最近在做什么呢？", "in_chat": False, "in_quiet_time": False})

        finally:
            db.close()
    except Exception as e:
        logger.error(f"获取问候语出错: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/admin/inventory', methods=['GET'])
def admin_inventory():
    """管理员查看用户库存页面"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        selected_user_id = request.args.get('user_id', type=int)

        users = db.query(User).all()

        inventory_items = []
        inventory_uploads = []

        try:
            query = db.query(InventoryItem)
            if selected_user_id:
                inventory_uploads = db.query(InventoryUpload.id).filter(
                    InventoryUpload.user_id == selected_user_id
                ).all()
                upload_ids = [upload.id for upload in inventory_uploads]
                query = query.filter(InventoryItem.inventory_upload_id.in_(upload_ids))

            inventory_items = query.join(
                InventoryUpload, InventoryItem.inventory_upload_id == InventoryUpload.id
            ).join(
                User, InventoryUpload.user_id == User.id
            ).order_by(InventoryItem.updated_at.desc()).all()

            inventory_uploads = db.query(InventoryUpload).join(
                User, InventoryUpload.user_id == User.id
            ).order_by(InventoryUpload.upload_time.desc()).all()
        except Exception as e:
            logger.error(f"查询库存数据出错: {str(e)}")
            return render_template('admin_inventory.html',
                                   users=users,
                                   selected_user_id=selected_user_id,
                                   inventory_items=[],
                                   inventory_uploads=[],
                                   message=f"查询库存数据出错: {str(e)}",
                                   message_type="danger")

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template(
            'admin_inventory.html',
            users=users,
            selected_user_id=selected_user_id,
            inventory_items=inventory_items,
            inventory_uploads=inventory_uploads,
            message=message,
            message_type=message_type
        )
    except Exception as e:
        logger.error(f"加载管理员库存页面出错: {str(e)}")
        return render_template('admin_inventory.html',
                               users=db.query(User).all() if 'db' in locals() else [],
                               selected_user_id=selected_user_id if 'selected_user_id' in locals() else None,
                               inventory_items=[],
                               inventory_uploads=[],
                               message=f"加载库存数据出错: {str(e)}",
                               message_type="danger")
    finally:
        db.close()


@app.route('/admin/order_management', methods=['GET'])
def admin_order_management():
    """管理员订单管理页面"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        selected_user_id = request.args.get('user_id', type=int)
        status_filter = request.args.get('status')

        users = db.query(User).all()

        query = db.query(Order)
        if selected_user_id:
            query = query.filter(Order.user_id == selected_user_id)

        if status_filter:
            query = query.filter(Order.status == status_filter)

        orders = query.join(
            User, Order.user_id == User.id
        ).order_by(Order.created_at.desc()).all()

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template(
            'admin_order_management.html',
            users=users,
            selected_user_id=selected_user_id,
            status_filter=status_filter,
            orders=orders,
            message=message,
            message_type=message_type
        )
    except Exception as e:
        logger.error(f"加载管理员订单页面出错: {str(e)}")
        return render_template('admin_order_management.html', message=f"加载订单数据出错: {str(e)}",
                               message_type="danger")
    finally:
        db.close()


@app.route('/admin/order_detail/<int:order_id>', methods=['GET'])
def admin_order_detail(order_id):
    """管理员查看订单详情页面"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return redirect(url_for('admin_order_management', message='订单不存在', message_type='danger'))

        return render_template(
            'admin_order_detail.html',
            order=order,
            message=request.args.get('message'),
            message_type=request.args.get('message_type', 'info')
        )
    except Exception as e:
        logger.error(f"加载订单详情页面出错: {str(e)}")
        return redirect(url_for('admin_order_management', message=f"加载订单详情出错: {str(e)}", message_type="danger"))
    finally:
        db.close()


@app.route('/admin/update_order_status/<int:order_id>/<status>', methods=['GET'])
def admin_update_order_status(order_id, status):
    """管理员更新订单状态"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return redirect(url_for('admin_order_management', message='订单不存在', message_type='danger'))

        valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
        if status not in valid_statuses:
            return redirect(
                url_for('admin_order_detail', order_id=order_id, message='无效的订单状态', message_type='danger'))

        order.status = status
        order.updated_at = datetime.now()
        db.commit()

        status_text = {
            'pending': '待处理',
            'processing': '处理中',
            'completed': '已完成',
            'cancelled': '已取消'
        }

        return redirect(url_for('admin_order_detail', order_id=order_id,
                                message=f'订单状态已更新为: {status_text.get(status, status)}', message_type='success'))
    except Exception as e:
        logger.error(f"更新订单状态出错: {str(e)}")
        return redirect(url_for('admin_order_detail', order_id=order_id, message=f"更新订单状态出错: {str(e)}",
                                message_type="danger"))
    finally:
        db.close()


@app.route('/admin/sales_statistics', methods=['GET'])
def admin_sales_statistics():
    """管理员销售统计页面"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_date = datetime.now() - timedelta(days=30)

        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
        else:
            end_date = datetime.now()

        total_sales = 0
        total_orders = 0
        total_items = 0
        daily_sales = []
        product_sales = []
        user_sales = []
        recent_sales = []
        chart_labels = []
        chart_data = []
        user_labels = []
        user_data = []
        top_products = []

        try:
            sales_query = db.query(Sale).filter(
                Sale.sale_date.between(start_date, end_date)
            )

            total_sales = db.query(func.sum(Sale.total_amount)).filter(
                Sale.sale_date.between(start_date, end_date)
            ).scalar() or 0

            total_orders = db.query(func.count(Order.id)).filter(
                Order.created_at.between(start_date, end_date),
                Order.status.in_(['completed', 'processing'])
            ).scalar() or 0

            daily_sales = db.query(
                func.date(Sale.sale_date).label('date'),
                func.sum(Sale.total_amount).label('amount')
            ).filter(
                Sale.sale_date.between(start_date, end_date)
            ).group_by(
                func.date(Sale.sale_date)
            ).order_by(
                func.date(Sale.sale_date)
            ).all()

            product_sales = db.query(
                Sale.product_name,
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.total_amount).label('amount')
            ).filter(
                Sale.sale_date.between(start_date, end_date)
            ).group_by(
                Sale.product_name
            ).order_by(
                func.sum(Sale.total_amount).desc()
            ).limit(10).all()

            user_sales = db.query(
                User.username,
                func.sum(Sale.total_amount).label('amount')
            ).join(
                User, Sale.user_id == User.id
            ).filter(
                Sale.sale_date.between(start_date, end_date)
            ).group_by(
                User.username
            ).order_by(
                func.sum(Sale.total_amount).desc()
            ).limit(10).all()

            chart_labels = [str(item.date) for item in daily_sales]
            chart_data = [float(item.amount) for item in daily_sales]

            user_labels = [item.username for item in user_sales]
            user_data = [float(item.amount) for item in user_sales]

            recent_sales = db.query(Sale).join(
                User, Sale.user_id == User.id
            ).filter(
                Sale.sale_date.between(start_date, end_date)
            ).order_by(
                Sale.sale_date.desc()
            ).limit(10).all()

            total_items = db.query(func.sum(Sale.quantity)).filter(
                Sale.sale_date.between(start_date, end_date)
            ).scalar() or 0

            top_products = []
            for item in product_sales:
                top_products.append({
                    'product_name': item.product_name,
                    'total_quantity': item.quantity,
                    'total_amount': item.amount
                })
        except Exception as e:
            logger.error(f"查询销售数据出错: {str(e)}")

        sales_stats = {
            'total_amount': total_sales,
            'total_orders': total_orders,
            'total_items': total_items,
            'avg_order_value': total_sales / total_orders if total_orders > 0 else 0
        }

        try:
            users = db.query(User).all()
        except Exception as e:
            logger.error(f"查询用户列表出错: {str(e)}")
            users = []

        selected_user_id = request.args.get('user_id', type=int)
        period = request.args.get('period', 'month')

        return render_template(
            'admin_sales_statistics.html',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            sales_stats=sales_stats,
            chart_labels=chart_labels,
            chart_data=chart_data,
            user_labels=user_labels,
            user_data=user_data,
            calendar_labels=chart_labels,  # 使用相同的标签数据
            calendar_data=chart_data,  # 使用相同的图表数据
            top_products=top_products,
            recent_sales=recent_sales,
            users=users,
            selected_user_id=selected_user_id,
            period=period,
            message=request.args.get('message'),
            message_type=request.args.get('message_type', 'info')
        )
    except Exception as e:
        logger.error(f"加载销售统计页面出错: {str(e)}")
        return render_template('admin_sales_statistics.html',
                               start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                               end_date=datetime.now().strftime('%Y-%m-%d'),
                               sales_stats={'total_amount': 0, 'total_orders': 0, 'total_items': 0,
                                            'avg_order_value': 0},
                               chart_labels=[],
                               chart_data=[],
                               user_labels=[],
                               user_data=[],
                               calendar_labels=[],
                               calendar_data=[],
                               top_products=[],
                               recent_sales=[],
                               users=[],
                               selected_user_id=None,
                               period='month',
                               message=f"加载销售数据出错: {str(e)}",
                               message_type="danger")
    finally:
        db.close()


@app.route('/admin/download_inventory/<int:upload_id>', methods=['GET'])
def admin_download_inventory(upload_id):
    """管理员下载用户上传的库存文件"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    try:
        upload = db.query(InventoryUpload).filter(InventoryUpload.id == upload_id).first()

        if not upload:
            return redirect(url_for('admin_inventory', message='文件不存在', message_type='danger'))

        if not os.path.exists(upload.file_path):
            return redirect(url_for('admin_inventory', message='文件已被删除', message_type='danger'))

        return send_file(
            upload.file_path,
            as_attachment=True,
            download_name=upload.original_filename or upload.filename
        )
    except Exception as e:
        logger.error(f"下载库存文件出错: {str(e)}")
        return redirect(url_for('admin_inventory', message=f"下载文件出错: {str(e)}", message_type="danger"))
    finally:
        db.close()


@app.route('/admin/view_user_inventory/<int:user_id>', methods=['GET'])
def admin_view_user_inventory(user_id):
    """管理员查看特定用户的库存"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    return redirect(url_for('admin_inventory', user_id=user_id))


@app.route('/user/inventory', methods=['GET'])
def user_inventory():
    """用户库存管理页面"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        inventory_uploads = db.query(InventoryUpload).filter(
            InventoryUpload.user_id == user.id
        ).order_by(InventoryUpload.created_at.desc()).all()

        latest_inventory = db.query(InventoryUpload).filter(
            InventoryUpload.user_id == user.id,
            InventoryUpload.status == 'success'
        ).order_by(InventoryUpload.created_at.desc()).first()

        from database import InventoryItem
        inventory_items = db.query(InventoryItem).join(InventoryUpload).filter(
            InventoryUpload.user_id == user.id,
            InventoryUpload.status == 'success'
        ).order_by(InventoryItem.updated_at.desc()).all()

        latest_items = {}
        for item in inventory_items:
            if item.product_id:
                if item.product_id not in latest_items or item.updated_at > latest_items[item.product_id].updated_at:
                    latest_items[item.product_id] = item
            else:
                key = f"name_{item.product_name}"
                if key not in latest_items or item.updated_at > latest_items[key].updated_at:
                    latest_items[key] = item

        inventory_items = list(latest_items.values())

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template(
            'user_inventory.html',
            user=user,
            inventory_uploads=inventory_uploads,
            inventory_items=inventory_items,
            latest_inventory=latest_inventory,
            message=message,
            message_type=message_type
        )
    except Exception as e:
        logger.error(f"处理请求出错: {str(e)}")
        return redirect(url_for('user_dashboard', message='处理请求失败', message_type='danger'))
    finally:
        db.close()


@app.route('/user/orders')
def user_orders():
    """用户订单管理页面"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        orders = db.query(Order).filter(
            Order.user_id == user.id
        ).order_by(Order.created_at.desc()).all()

        pending_count = db.query(Order).filter(
            Order.user_id == user.id,
            Order.status == 'pending'
        ).count()

        processing_count = db.query(Order).filter(
            Order.user_id == user.id,
            Order.status == 'processing'
        ).count()

        completed_count = db.query(Order).filter(
            Order.user_id == user.id,
            Order.status == 'completed'
        ).count()

        total_amount = db.query(func.sum(Order.total_amount)).filter(
            Order.user_id == user.id
        ).scalar() or 0

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template(
            'user_orders.html',
            user=user,
            orders=orders,
            pending_count=pending_count,
            processing_count=processing_count,
            completed_count=completed_count,
            total_amount=total_amount,
            message=message,
            message_type=message_type
        )
    except Exception as e:
        logger.error(f"处理请求出错: {str(e)}")
        return redirect(url_for('user_dashboard', message='处理请求失败', message_type='danger'))
    finally:
        db.close()


@app.route('/user/upload_inventory', methods=['POST'])
def user_upload_inventory():
    """处理用户上传库存文件"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        if 'inventory_file' not in request.files:
            return redirect(url_for('user_profile', message='未选择文件', message_type='danger'))

        file = request.files['inventory_file']

        if file.filename == '':
            return redirect(url_for('user_profile', message='未选择文件', message_type='danger'))

        if file:
            allowed_extensions = {'csv', 'xlsx', 'xls'}
            if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                return redirect(
                    url_for('user_profile', message='不支持的文件格式，请上传CSV或Excel文件', message_type='danger'))

            upload_dir = os.path.join(get_base_dir(), 'uploads', str(user_id))
            os.makedirs(upload_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{file.filename}"
            file_path = os.path.join(upload_dir, filename)

            file.save(file_path)

            from database import InventoryUpload
            upload_record = InventoryUpload(
                user_id=user.id,
                filename=filename,
                original_filename=file.filename,
                file_path=file_path,
                status='processing',
                upload_time=datetime.now()
            )
            db.add(upload_record)
            db.commit()

            try:
                from inventory_processor import process_inventory_file
                result = process_inventory_file(file_path, user_id, upload_record.id)

                upload_record.status = 'success'
                upload_record.notes = f"处理成功: {result.get('count', 0)}条记录"
                db.commit()

                return redirect(url_for('user_profile', message=f'文件上传成功，已处理{result.get("count", 0)}条记录',
                                        message_type='success'))
            except Exception as e:
                logger.error(f"处理库存文件失败: {str(e)}")
                upload_record.status = 'failed'
                upload_record.notes = f"处理失败: {str(e)}"
                db.commit()

                return redirect(
                    url_for('user_profile', message=f'文件上传成功，但处理失败: {str(e)}', message_type='warning'))
    except Exception as e:
        logger.error(f"上传库存文件出错: {str(e)}")
        return redirect(url_for('user_profile', message=f'上传失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/user/download_inventory/<int:upload_id>', methods=['GET'])
def user_download_inventory(upload_id):
    """下载用户上传的库存文件"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        upload = db.query(InventoryUpload).filter(
            InventoryUpload.id == upload_id,
            InventoryUpload.user_id == user.id
        ).first()

        if not upload:
            return redirect(url_for('user_inventory', message='文件不存在或无权访问', message_type='danger'))

        if not os.path.exists(upload.file_path):
            return redirect(url_for('user_inventory', message='文件不存在', message_type='danger'))

        return send_file(
            upload.file_path,
            as_attachment=True,
            download_name=upload.filename
        )
    except Exception as e:
        logger.error(f"下载库存文件出错: {str(e)}")
        return redirect(url_for('user_inventory', message=f'下载失败: {str(e)}', message_type='danger'))
    finally:
        db.close()


@app.route('/user/sales')
def user_sales():
    """用户销售统计页面"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        period = request.args.get('period', 'month')

        if period == 'today':
            from_date = datetime.now().strftime('%Y-%m-%d')
            to_date = datetime.now().strftime('%Y-%m-%d')
        elif period == 'week':
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            to_date = datetime.now().strftime('%Y-%m-%d')
        elif period == 'month':
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            to_date = datetime.now().strftime('%Y-%m-%d')
        elif period == 'year':
            from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            to_date = datetime.now().strftime('%Y-%m-%d')

        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')

        from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
        to_datetime = datetime.strptime(to_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')

        sales = db.query(Sale).filter(
            Sale.user_id == user.id,
            Sale.sale_date >= from_datetime,
            Sale.sale_date <= to_datetime
        ).order_by(Sale.sale_date.desc()).all()

        total_sales = db.query(func.sum(Sale.total_amount)).filter(
            Sale.user_id == user.id,
            Sale.sale_date >= from_datetime,
            Sale.sale_date <= to_datetime
        ).scalar() or 0

        total_items = db.query(func.sum(Sale.quantity)).filter(
            Sale.user_id == user.id,
            Sale.sale_date >= from_datetime,
            Sale.sale_date <= to_datetime
        ).scalar() or 0

        total_orders = db.query(func.count(func.distinct(Sale.order_id))).filter(
            Sale.user_id == user.id,
            Sale.sale_date >= from_datetime,
            Sale.sale_date <= to_datetime,
            Sale.order_id != None
        ).scalar() or 0

        avg_order_value = 0
        if total_orders > 0:
            avg_order_value = round(total_sales / total_orders, 2)

        top_products = db.query(
            Sale.product_name,
            func.sum(Sale.quantity).label('total_quantity'),
            func.sum(Sale.total_amount).label('total_amount')
        ).filter(
            Sale.user_id == user.id,
            Sale.sale_date >= from_datetime,
            Sale.sale_date <= to_datetime
        ).group_by(Sale.product_name).order_by(func.sum(Sale.quantity).desc()).limit(5).all()

        sales_trend = []
        chart_labels = []
        chart_data = []

        if period == 'today':
            for hour in range(24):
                hour_start = datetime.strptime(f"{from_date} {hour:02d}:00:00", '%Y-%m-%d %H:%M:%S')
                hour_end = datetime.strptime(f"{from_date} {hour:02d}:59:59", '%Y-%m-%d %H:%M:%S')

                hourly_sales = db.query(func.sum(Sale.total_amount)).filter(
                    Sale.user_id == user.id,
                    Sale.sale_date >= hour_start,
                    Sale.sale_date <= hour_end
                ).scalar() or 0

                chart_labels.append(f"{hour:02d}:00")
                chart_data.append(hourly_sales)
        else:
            current_date = from_datetime
            while current_date <= to_datetime:
                next_date = current_date + timedelta(days=1)
                daily_sales = db.query(func.sum(Sale.total_amount)).filter(
                    Sale.user_id == user.id,
                    Sale.sale_date >= current_date,
                    Sale.sale_date < next_date
                ).scalar() or 0

                chart_labels.append(current_date.strftime('%m-%d'))
                chart_data.append(daily_sales)
                current_date = next_date

        sales_stats = {
            'total_amount': total_sales,
            'total_orders': total_orders,
            'total_items': total_items,
            'avg_order_value': avg_order_value
        }

        recent_sales = db.query(Sale).filter(
            Sale.user_id == user.id
        ).order_by(Sale.sale_date.desc()).limit(10).all()

        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')

        return render_template(
            'user_sales.html',
            user=user,
            sales=sales,
            total_sales=total_sales,
            total_items=total_items,
            top_products=top_products,
            sales_trend=sales_trend,
            from_date=from_date,
            to_date=to_date,
            message=message,
            message_type=message_type,
            sales_stats=sales_stats,
            chart_labels=chart_labels,
            chart_data=chart_data,
            recent_sales=recent_sales,
            period=period
        )
    except Exception as e:
        logger.error(f"处理请求出错: {str(e)}")
        return redirect(url_for('user_dashboard', message='处理请求失败', message_type='danger'))
    finally:
        db.close()


@app.route('/user/update_inventory_item', methods=['POST'])
def user_update_inventory_item():
    """更新库存商品信息"""
    if not session.get('user_id'):
        return jsonify({"error": "未登录"}), 401

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return jsonify({"error": "用户不存在"}), 403

        item_id = request.form.get('item_id')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        notes = request.form.get('notes', '')

        if not item_id or not quantity:
            return jsonify({"error": "缺少必要参数"}), 400

        try:
            quantity = int(quantity)
            if quantity < 0:
                return jsonify({"error": "数量不能为负数"}), 400
        except ValueError:
            return jsonify({"error": "数量必须为整数"}), 400

        if price:
            try:
                price = float(price)
                if price < 0:
                    return jsonify({"error": "价格不能为负数"}), 400
            except ValueError:
                return jsonify({"error": "价格格式不正确"}), 400
        else:
            price = None

        from database import InventoryItem
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item:
            return jsonify({"error": "商品不存在"}), 404

        upload = db.query(InventoryUpload).filter(
            InventoryUpload.id == item.inventory_upload_id,
            InventoryUpload.user_id == user.id
        ).first()

        if not upload:
            return jsonify({"error": "无权访问此商品"}), 403

        item.quantity = quantity
        item.price = price

        if price is not None:
            item.total_price = price * quantity
        else:
            item.total_price = None

        item.notes = notes
        item.updated_at = datetime.now()

        db.commit()

        return jsonify({
            "success": True,
            "message": "商品信息已更新",
            "data": {
                "id": item.id,
                "quantity": item.quantity,
                "price": item.price,
                "total_price": item.total_price,
                "notes": item.notes,
                "updated_at": item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        db.rollback()
        logger.error(f"更新商品信息出错: {str(e)}")
        return jsonify({"error": f"更新失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route('/user/order/<int:order_id>')
def user_order_detail(order_id):
    """订单详情页面"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        from database import Order
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user.id
        ).first()

        if not order:
            return redirect(url_for('user_orders', message='订单不存在', message_type='danger'))

        return render_template(
            'user_order_detail.html',
            user=user,
            order=order
        )
    except Exception as e:
        logger.error(f"获取订单详情出错: {str(e)}")
        return redirect(url_for('user_orders', message='获取订单详情失败', message_type='danger'))
    finally:
        db.close()


@app.route('/user/sales_statistics')
def user_sales_statistics():
    """用户销售统计详情页面"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        from database import Sale, Order, OrderItem
        from sqlalchemy import func

        period = request.args.get('period', 'all')
        today = datetime.now().date()

        query = db.query(Sale).filter(Sale.user_id == user.id)

        if period == 'today':
            query = query.filter(func.date(Sale.sale_date) == today)
        elif period == 'week':
            week_start = today - timedelta(days=today.weekday())
            query = query.filter(func.date(Sale.sale_date) >= week_start)
        elif period == 'month':
            month_start = today.replace(day=1)
            query = query.filter(func.date(Sale.sale_date) >= month_start)
        elif period == 'year':
            year_start = today.replace(month=1, day=1)
            query = query.filter(func.date(Sale.sale_date) >= year_start)

        sales_stats = {
            'total_amount': query.with_entities(func.sum(Sale.total_amount)).scalar() or 0,
            'total_orders': query.with_entities(func.count(func.distinct(Sale.order_id))).scalar() or 0,
            'total_items': query.with_entities(func.sum(Sale.quantity)).scalar() or 0,
            'avg_order_value': 0
        }

        if sales_stats['total_orders'] > 0:
            sales_stats['avg_order_value'] = sales_stats['total_amount'] / sales_stats['total_orders']

        top_products = query.with_entities(
            Sale.product_name,
            func.sum(Sale.quantity).label('total_quantity'),
            func.sum(Sale.total_amount).label('total_amount')
        ).group_by(Sale.product_name).order_by(func.sum(Sale.quantity).desc()).limit(10).all()

        recent_sales = query.order_by(Sale.sale_date.desc()).limit(20).all()

        thirty_days_ago = today - timedelta(days=30)
        trend_data = db.query(
            func.date(Sale.sale_date).label('date'),
            func.sum(Sale.total_amount).label('amount')
        ).filter(
            Sale.user_id == user.id,
            func.date(Sale.sale_date) >= thirty_days_ago
        ).group_by(func.date(Sale.sale_date)).order_by(func.date(Sale.sale_date)).all()

        chart_labels = [str(item.date) for item in trend_data]
        chart_data = [float(item.amount) for item in trend_data]

        return render_template(
            'user_sales.html',
            user=user,
            sales_stats=sales_stats,
            top_products=top_products,
            recent_sales=recent_sales,
            chart_labels=chart_labels,
            chart_data=chart_data,
            period=period
        )
    except Exception as e:
        logger.error(f"获取销售统计出错: {str(e)}")
        return redirect(url_for('user_dashboard', message='获取销售统计失败', message_type='danger'))
    finally:
        db.close()


@app.route('/user/pay_order/<int:order_id>')
def user_pay_order(order_id):
    """支付订单"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        from database import Order
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user.id,
            Order.status == 'pending',
            Order.payment_status == 'unpaid'
        ).first()

        if not order:
            return redirect(url_for('user_orders', message='订单不存在或无法支付', message_type='danger'))

        order.payment_status = 'paid'
        order.status = 'processing'
        order.updated_at = datetime.now()

        from database import Sale
        for item in order.items:
            sale = Sale(
                user_id=user.id,
                order_id=order.id,
                product_name=item.product_name,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total_amount=item.total_price,
                sale_date=datetime.now(),
                payment_method='online'  # 这里应该根据实际支付方式设置
            )
            db.add(sale)

        db.commit()

        return redirect(url_for('user_orders', message='订单支付成功', message_type='success'))
    except Exception as e:
        db.rollback()
        logger.error(f"支付订单出错: {str(e)}")
        return redirect(url_for('user_orders', message='支付失败', message_type='danger'))
    finally:
        db.close()


@app.route('/user/cancel_order/<int:order_id>')
def user_cancel_order(order_id):
    """取消订单"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return redirect(url_for('user_login'))

        from database import Order
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user.id,
            Order.status == 'pending',
            Order.payment_status == 'unpaid'
        ).first()

        if not order:
            return redirect(url_for('user_orders', message='订单不存在或无法取消', message_type='danger'))

        order.status = 'cancelled'
        order.updated_at = datetime.now()
        db.commit()

        return redirect(url_for('user_orders', message='订单已取消', message_type='success'))
    except Exception as e:
        db.rollback()
        logger.error(f"取消订单出错: {str(e)}")
        return redirect(url_for('user_orders', message='取消失败', message_type='danger'))
    finally:
        db.close()


@app.route('/user/delete_inventory_item', methods=['POST'])
def user_delete_inventory_item():
    """删除库存商品"""
    if not session.get('user_id'):
        return jsonify({"error": "未登录"}), 401

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return jsonify({"error": "用户不存在"}), 403

        item_id = request.form.get('item_id')

        if not item_id:
            return jsonify({"error": "缺少必要参数"}), 400

        from database import InventoryItem
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item:
            return jsonify({"error": "商品不存在"}), 404

        upload = db.query(InventoryUpload).filter(
            InventoryUpload.id == item.inventory_upload_id,
            InventoryUpload.user_id == user.id
        ).first()

        if not upload:
            return jsonify({"error": "无权删除此商品"}), 403

        product_name = item.product_name
        product_id = item.product_id

        db.delete(item)
        db.commit()

        logger.info(f"用户 {user_id} 删除了商品: {product_name}, ID: {product_id}")

        return jsonify({
            "success": True,
            "message": "商品已删除",
            "data": {
                "id": item_id,
                "product_name": product_name,
                "product_id": product_id
            }
        })
    except Exception as e:
        db.rollback()
        logger.error(f"删除商品出错: {str(e)}")
        return jsonify({"error": f"删除失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route('/user/add_inventory_item', methods=['POST'])
def user_add_inventory_item():
    """添加新的库存商品"""
    if not session.get('user_id'):
        return jsonify({"error": "未登录"}), 401

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return jsonify({"error": "用户不存在"}), 403

        product_name = request.form.get('product_name')
        product_id = request.form.get('product_id', '')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        notes = request.form.get('notes', '')

        if not product_name or not quantity:
            return jsonify({"error": "缺少必要参数"}), 400

        try:
            quantity = int(quantity)
            if quantity < 0:
                return jsonify({"error": "数量不能为负数"}), 400
        except ValueError:
            return jsonify({"error": "数量必须为整数"}), 400

        if price:
            try:
                price = float(price)
                if price < 0:
                    return jsonify({"error": "价格不能为负数"}), 400
            except ValueError:
                return jsonify({"error": "价格格式不正确"}), 400
        else:
            price = None

        upload_record = InventoryUpload(
            user_id=user.id,
            filename=f"web_add_{datetime.now().strftime('%Y%m%d%H%M%S')}.json",
            original_filename="网页添加",
            file_path="",
            status='success',
            upload_time=datetime.now(),
            type="inventory",
            notes="通过网页添加"
        )
        db.add(upload_record)
        db.flush()

        total_price = price * quantity if price else None

        from database import InventoryItem
        inventory_item = InventoryItem(
            inventory_upload_id=upload_record.id,
            product_name=product_name,
            product_id=product_id if product_id else None,
            quantity=quantity,
            price=price,
            total_price=total_price,
            notes=notes
        )
        db.add(inventory_item)
        db.commit()

        logger.info(f"用户 {user_id} 添加了新商品: {product_name}, 数量: {quantity}")

        return jsonify({
            "success": True,
            "message": "商品添加成功",
            "data": {
                "id": inventory_item.id,
                "product_name": inventory_item.product_name,
                "product_id": inventory_item.product_id,
                "quantity": inventory_item.quantity,
                "price": inventory_item.price,
                "total_price": inventory_item.total_price,
                "notes": inventory_item.notes,
                "updated_at": inventory_item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        db.rollback()
        logger.error(f"添加商品出错: {str(e)}")
        return jsonify({"error": f"添加失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route('/user/upload_product_image', methods=['POST'])
def user_upload_product_image():
    """上传商品图片"""
    if not session.get('user_id'):
        return jsonify({"error": "未登录"}), 401

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return jsonify({"error": "用户不存在"}), 403

        item_id = request.form.get('item_id')
        if not item_id:
            return jsonify({"error": "缺少商品ID"}), 400

        if 'image' not in request.files:
            return jsonify({"error": "未选择图片文件"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "未选择图片文件"}), 400

        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({"error": "不支持的图片格式，请上传JPG、PNG或GIF文件"}), 400

        from database import InventoryItem
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item:
            return jsonify({"error": "商品不存在"}), 404

        upload = db.query(InventoryUpload).filter(
            InventoryUpload.id == item.inventory_upload_id,
            InventoryUpload.user_id == user.id
        ).first()

        if not upload:
            return jsonify({"error": "无权访问此商品"}), 403

        upload_dir = os.path.join(get_base_dir(), 'uploads', 'product_images', str(user_id))
        os.makedirs(upload_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{timestamp}_{item_id}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)

        file.save(file_path)
        file_size = os.path.getsize(file_path)

        if file_size > 5 * 1024 * 1024:
            os.remove(file_path)
            return jsonify({"error": "图片文件大小不能超过5MB"}), 400

        from database import ProductImage
        product_image = ProductImage(
            inventory_item_id=item.id,
            image_path=file_path,
            original_filename=file.filename,
            file_size=file_size
        )
        db.add(product_image)
        db.commit()

        image_url = f"/static/uploads/product_images/{user_id}/{filename}"

        logger.info(f"用户 {user_id} 为商品 {item_id} 上传了图片: {filename}")

        return jsonify({
            "success": True,
            "message": "图片上传成功",
            "data": {
                "image_id": product_image.id,
                "image_url": image_url,
                "filename": filename,
                "file_size": file_size
            }
        })
    except Exception as e:
        db.rollback()
        logger.error(f"上传图片出错: {str(e)}")
        return jsonify({"error": f"上传失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route('/api/sync_contacts', methods=['POST'])
def sync_contacts():
    """同步微信联系人 (HTTP API)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为JSON格式"}), 400

        owner_id = data.get("owner_id")  # 系统用户ID
        wechat_id = data.get("wechat_id")  # 微信账号ID
        contacts = data.get("contacts", [])

        if not owner_id or not wechat_id or not contacts:
            return jsonify({"error": "缺少必要参数"}), 400

        result = process_contact_sync(owner_id, wechat_id, contacts)
        if "error" in result:
            return jsonify(result), result.get("status_code", 500)

        room_id = f"wechat_{wechat_id}"
        socketio.emit('contacts_updated', {
            'wechat_id': wechat_id,
            'sync_count': result.get("sync_count", 0),
            'timestamp': datetime.now().isoformat()
        }, to=room_id)

        return jsonify(result)
    except Exception as e:
        logger.error(f"同步联系人失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@socketio.on('sync_contacts')
def handle_sync_contacts(data):
    """同步微信联系人 (WebSocket)"""
    try:
        user_id = data.get("user_id")
        wechat_id = data.get("wechat_id")
        contacts = data.get("contacts", [])

        if not user_id or not wechat_id or not contacts:
            emit('error', {'message': '同步联系人缺少必要参数'})
            return

        if user_id not in user_socket_map:
            emit('error', {'message': '未认证，请先进行认证', 'code': 'auth_required'})
            return

        result = process_contact_sync(user_id, wechat_id, contacts)

        if "error" in result:
            emit('error', {'message': result.get("error")})
            return

        emit('contacts_synced', {
            'wechat_id': wechat_id,
            'sync_count': result.get("sync_count", 0),
            'timestamp': datetime.now().isoformat()
        })

        room_id = f"wechat_{wechat_id}"
        socketio.emit('contacts_updated', {
            'wechat_id': wechat_id,
            'sync_count': result.get("sync_count", 0),
            'timestamp': datetime.now().isoformat()
        }, to=room_id)

        logger.info(
            f"通过WebSocket同步联系人成功: 用户={user_id}, 微信ID={wechat_id}, 数量={result.get('sync_count', 0)}")
    except Exception as e:
        logger.error(f"通过WebSocket同步联系人失败: {str(e)}")
        emit('error', {'message': '同步联系人失败：服务器内部错误'})


def process_contact_sync(owner_id, wechat_id, contacts):
    """处理联系人同步逻辑 (共用函数)"""
    try:
        db = next(get_db())
        try:
            owner = db.query(User).filter(User.user_id == owner_id).first()
            if not owner:
                return {"error": "用户不存在", "status_code": 404}

            # 查找微信账号
            wechat_account = db.query(WechatContact).filter(
                WechatContact.wechat_id == wechat_id,
                WechatContact.owner_id == owner.id,
                WechatContact.parent_id == None  # 确保是账号而不是联系人
            ).first()
            print("调试信息 >>> owner_id:", owner_id)
            print("调试信息 >>> owner.id:", owner.id)
            print("调试信息 >>> wechat_account 查询结果:", wechat_account)
            if not wechat_account:
                return {"error": "微信账号不存在", "status_code": 404}

            sync_count = 0

            max_contacts = min(len(contacts), 5000)  # 最多同步5000个联系人

            for contact_data in contacts[:max_contacts]:
                contact_wechat_id = contact_data.get("wechat_id")
                if not contact_wechat_id:
                    continue

                contact = db.query(WechatContact).filter(
                    WechatContact.wechat_id == contact_wechat_id,
                    WechatContact.parent_id == wechat_account.id
                ).first()

                if not contact:
                    contact = WechatContact(
                        wechat_id=contact_wechat_id,
                        owner_id=owner.id,
                        parent_id=wechat_account.id
                    )
                    db.add(contact)

                # 更新联系人信息
                contact.nickname = contact_data.get("nickname", contact.nickname)
                contact.remark = contact_data.get("remark", contact.remark)
                contact.is_group = contact_data.get("is_group", contact.is_group)
                contact.avatar = contact_data.get("avatar", contact.avatar)
                contact.last_sync_time = datetime.utcnow()

                sync_count += 1

            db.commit()

            return {
                "success": True,
                "sync_count": sync_count,
                "message": f"成功同步 {sync_count} 个联系人"
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"处理联系人同步失败: {str(e)}")
        return {"error": "服务器内部错误", "status_code": 500}


@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """获取联系人列表"""
    try:
        owner_id = request.args.get('owner_id')
        wechat_id = request.args.get('wechat_id')
        is_group = request.args.get('is_group')
        search = request.args.get('search')

        if not owner_id:
            return jsonify({"error": "缺少owner_id参数"}), 400

        db = next(get_db())
        owner = db.query(User).filter(User.user_id == owner_id).first()

        if not owner:
            return jsonify({"error": "用户不存在"}), 404

        if wechat_id:
            # 查找微信账号
            wechat_account = db.query(WechatContact).filter(
                WechatContact.wechat_id == wechat_id,
                WechatContact.owner_id == owner.id,
                WechatContact.parent_id == None  # 确保是账号而不是联系人
            ).first()

            if not wechat_account:
                return jsonify({"error": "微信账号不存在"}), 404

            # 查询该微信账号下的联系人
            query = db.query(WechatContact).filter(
                WechatContact.parent_id == wechat_account.id
            )
        else:
            # 如果没有指定微信账号，则查询所有联系人
            query = db.query(WechatContact).filter(
                WechatContact.owner_id == owner.id,
                WechatContact.parent_id != None  # 只查询联系人，不包括账号
            )

        if is_group is not None:
            is_group_bool = is_group.lower() == 'true'
            query = query.filter(WechatContact.is_group == is_group_bool)

        if search:
            query = query.filter(
                or_(
                    WechatContact.nickname.like(f"%{search}%"),
                    WechatContact.remark.like(f"%{search}%"),
                    WechatContact.wechat_id.like(f"%{search}%")
                )
            )

        query = query.order_by(desc(WechatContact.last_active_at))

        contacts = query.all()

        contact_list = []
        for contact in contacts:
            # 查询该联系人最后一条消息
            last_msg = db.query(WechatMessage).filter(
                WechatMessage.contact_id == contact.id
            ).order_by(desc(WechatMessage.created_at)).first()

            contact_list.append({
                "id": contact.id,
                "wechat_id": contact.wechat_id,
                "nickname": contact.nickname,
                "remark": contact.remark,
                "is_group": contact.is_group,
                "avatar": contact.avatar,
                "ai_reply_enabled": contact.ai_reply_enabled,
                "keyword_filter_enabled": contact.keyword_filter_enabled if hasattr(contact,
                                                                                    'keyword_filter_enabled') else False,
                "ai_strategy_id": contact.ai_strategy_id if hasattr(contact, 'ai_strategy_id') else None,
                "last_sync_time": contact.last_sync_time.strftime(
                    '%Y-%m-%d %H:%M:%S') if contact.last_sync_time else None,
                "last_active_at": contact.last_active_at.strftime(
                    '%Y-%m-%d %H:%M:%S') if contact.last_active_at else None,
                "unread_count": contact.unread_count if hasattr(contact, 'unread_count') else 0,
                # 新增，后端查出来发给前端的字段
                "last_message": last_msg.content if last_msg else "",
                "last_message_time": last_msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if last_msg else ""
            })

        return jsonify({"contacts": contact_list})
    except Exception as e:
        logger.error(f"获取联系人列表失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/contacts/<int:contact_id>/clear_unread', methods=['POST'])
def clear_unread_count(contact_id):
    """清除联系人未读消息计数"""
    try:
        if not request.is_json:
            return jsonify({"error": "请求必须为JSON格式"}), 400
        data = request.json
        owner_id = data.get("owner_id")
        db = next(get_db())
        contact = db.query(WechatContact).filter(WechatContact.id == contact_id).first()
        if not contact:
            return jsonify({"error": "联系人不存在"}), 404
        if owner_id and contact.owner_id != int(owner_id):
            return jsonify({"error": "权限不足"}), 403
        contact.unread_count = 0
        db.commit()
        return jsonify({"success": True, "contact_id": contact_id, "message": "未读消息计数已清除"})
    except Exception as e:
        logger.error(f"清除未读消息计数失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/set_ai_reply', methods=['POST'])
def set_ai_reply():
    """设置联系人AI回复开关"""
    try:
        data = request.get_json()
        print("接收到数据 >>>", data)

        if not data:
            print("调试 >>> 请求不是JSON格式")
            return jsonify({"error": "请求必须为JSON格式"}), 400

        owner_id = data.get("owner_id")  # 微信账号ID
        contact_id = data.get("contact_id")  # 联系人ID
        ai_reply_enabled = data.get("ai_reply_enabled")  # 是否启用AI回复
        keyword_filter_enabled = data.get("keyword_filter_enabled")  # 是否启用关键词过滤
        ai_strategy_id = data.get("ai_strategy_id")  # AI回复策略ID

        print(
            f"调试 >>> owner_id={owner_id}, contact_id={contact_id}, ai_reply_enabled={ai_reply_enabled}, keyword_filter_enabled={keyword_filter_enabled}, ai_strategy_id={ai_strategy_id}")

        if not owner_id or not contact_id or ai_reply_enabled is None:
            print("调试 >>> 缺少必要参数")
            return jsonify({"error": "缺少必要参数"}), 400

        db = next(get_db())
        owner = db.query(User).filter(User.user_id == owner_id).first()

        if not owner:
            print("调试 >>> 微信账号不存在")
            return jsonify({"error": "微信账号不存在"}), 404

        contact = db.query(WechatContact).filter(
            WechatContact.wechat_id == contact_id
            # WechatContact.owner_id == owner.id
        ).first()
        if not contact:
            print("调试 >>> 联系人不存在")
            return jsonify({"error": "联系人不存在"}), 404

        contact.ai_reply_enabled = ai_reply_enabled
        print(f"调试 >>> 设置 ai_reply_enabled = {ai_reply_enabled}")

        if keyword_filter_enabled is not None:
            contact.keyword_filter_enabled = keyword_filter_enabled
            print(f"调试 >>> 设置 keyword_filter_enabled = {keyword_filter_enabled}")

        if ai_strategy_id is not None:
            strategy = db.get(AIStrategy, ai_strategy_id)
            print("调试 >>> 查询AIStrategy结果:", strategy)
            if strategy:
                contact.ai_strategy_id = ai_strategy_id
                print(f"调试 >>> 设置 ai_strategy_id = {ai_strategy_id}")

        db.commit()
        print("调试 >>> 数据库提交成功")

        return jsonify({
            "success": True,
            "message": "成功更新联系人AI回复设置"
        })
    except Exception as e:
        logger.error(f"设置AI回复失败: {str(e)}")
        import traceback
        traceback.print_exc()  # 打印详细的异常信息
        return jsonify({"error": "服务器内部错误"}), 500


@socketio.on('authenticate')
def handle_authenticate(data):
    """WebSocket认证"""
    logger.info(f"收到认证数据: {data}")
    try:
        user_id = data.get('user_id')
        emit('auth_success', to=request.sid)
        print(f"用户 {user_id} 认证成功，已通知前端")
        if not user_id:
            emit('error', {'message': '认证失败：缺少user_id', 'code': 'auth_required'})
            return

        user_socket_map[user_id] = request.sid
        user_last_heartbeat[user_id] = datetime.now()

        join_room(user_id)

        if not hasattr(app, 'user_wechat_rooms'):
            app.user_wechat_rooms = {}

        if user_id not in app.user_wechat_rooms:
            app.user_wechat_rooms[user_id] = set()

        emit('authenticated', {'message': '认证成功', 'user_id': user_id})
        logger.info(f"用户 {user_id} 认证成功")
    except Exception as e:
        logger.error(f"WebSocket认证失败: {str(e)}")
        emit('error', {'message': f'认证失败：{str(e)}', 'code': 'auth_error'})
        emit('error', {'message': '认证失败：服务器内部错误'})


@socketio.on('join')
def handle_join(data):
    """加入聊天房间"""
    try:
        room = data.get('room')
        if room:
            join_room(room)
            emit('joined', {'room': room})
    except Exception as e:
        logger.error(f"加入房间失败: {str(e)}")
        emit('error', {'message': '加入房间失败'})


@socketio.on('join_wechat_room')
def handle_join_wechat_room(data):
    """处理加入微信房间请求"""
    try:
        user_id = data.get('user_id')
        wechat_id = data.get('wechat_id')

        if not user_id or not wechat_id:
            emit('error', {'message': '加入房间失败：缺少必要参数'})
            return

        if user_id not in user_socket_map:
            emit('error', {'message': '加入房间失败：用户未认证', 'code': 'auth_required'})
            return

        room_id = f"wechat_{wechat_id}"

        join_room(room_id)

        if not hasattr(app, 'user_wechat_rooms'):
            app.user_wechat_rooms = {}

        if user_id not in app.user_wechat_rooms:
            app.user_wechat_rooms[user_id] = set()

        app.user_wechat_rooms[user_id].add(room_id)

        emit('joined_wechat_room', {
            'wechat_id': wechat_id,
            'room_id': room_id,
            'status': 'ok'
        })

        logger.info(f"用户 {user_id} 加入微信房间: {room_id}")
    except Exception as e:
        logger.error(f"加入微信房间失败: {str(e)}")
        emit('error', {'message': f'加入房间失败: {str(e)}'})


@socketio.on('heartbeat')
def handle_heartbeat(data):
    """处理客户端心跳"""
    try:
        user_id = data.get('user_id')
        timestamp = data.get('timestamp')

        if not user_id:
            emit('error', {'message': '心跳包缺少user_id'})
            return

        if user_id in user_socket_map:
            user_last_heartbeat[user_id] = datetime.now()
            emit('heartbeat_ack', {
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'server_time': datetime.now().isoformat()
            })

            if user_id in user_message_queues and user_message_queues[user_id]:
                process_message_queue(user_id)
        else:
            emit('error', {'message': '未认证，请先进行认证', 'code': 'auth_required'})
    except Exception as e:
        logger.error(f"处理心跳包失败: {str(e)}")
        emit('error', {'message': '处理心跳包失败'})


@socketio.on('ack_message')
def handle_ack_message(data):
    """处理消息确认"""
    try:
        user_id = data.get('user_id')
        message_id = data.get('message_id')

        if not user_id or not message_id:
            emit('error', {'message': '消息确认缺少必要参数'})
            return

        db = next(get_db())
        message = db.query(WechatMessage).filter(WechatMessage.message_id == message_id).first()
        if message:
            message.ack_status = 'ack'
            db.commit()

        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.last_ack_id = message_id
            db.commit()

        if user_id in user_message_queues:
            user_message_queues[user_id] = [msg for msg in user_message_queues[user_id]
                                            if msg.get('id') != message_id]

        emit('message_ack_received', {
            'message_id': message_id,
            'status': 'ok',
            'timestamp': datetime.now().isoformat()
        })

        logger.debug(f"用户 {user_id} 确认消息 {message_id}")
    except Exception as e:
        logger.error(f"处理消息确认失败: {str(e)}")
        emit('error', {'message': '处理消息确认失败'})

import hashlib
@socketio.on('send_direct_message')
def handle_send_direct_message(data):
    """处理直接消息发送请求 (WebSocket)"""
    try:
        user_id = data.get('user_id')
        wechat_id = data.get('wechat_id')
        target_wechat_id = data.get('contact_id')  # 更清晰的命名
        content = data.get('content')
        content_type = data.get('content_type', 'text')
        send_type = data.get('send_type', 'active')

        if not all([user_id, wechat_id, target_wechat_id, content]):
            emit('error', {'message': '发送消息缺少必要参数'})
            return

        if user_id not in user_socket_map:
            emit('error', {'message': '未认证，请先进行认证', 'code': 'auth_required'})
            return

        # 使用更稳定的唯一 ID 生成方式
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
        unique_message_id = f"{user_id}_{int(time.time() * 1000)}_{content_hash}"

        message_data = {
            'id': unique_message_id,
            'wechat_id': wechat_id,
            'contact_id': target_wechat_id,
            'content': content,
            'content_type': content_type,
            'created_at': datetime.now().isoformat(),
            'require_ack': True,
            'send_type': send_type
        }

        room_id = f"wechat_{wechat_id}"
        socketio.emit('new_message', message_data, to=room_id)

        db: Session = next(get_db())
        logger.info(f"收到 WebSocket 消息：{data}")

        contact_db_obj = db.query(WechatContact).filter(
            WechatContact.wechat_id == target_wechat_id
        ).first()

        if not contact_db_obj:
            logger.error(f"未找到微信号为 {target_wechat_id} 的联系人，无法保存消息！")
            emit('error', {'message': f"未找到联系人: {target_wechat_id}"})
            return

        db_contact_id = contact_db_obj.id

        sender_id = user_id if send_type == 'active' else target_wechat_id

        message = WechatMessage(
            contact_id=db_contact_id,
            sender_id=sender_id,
            content=content,
            content_type=content_type,
            is_from_ai=False,
            status="sent",
            message_id=unique_message_id,
            ack_status="ack",
            created_at=datetime.now()
        )

        db.add(message)
        contact_db_obj.last_active_at = datetime.now()
        db.commit()

        logger.info(
            f"消息已保存到数据库：contact_id={db_contact_id}, sender_id={sender_id}, "
            f"content='{content}', content_type={content_type}, is_from_ai=False, "
            f"status='sent', created_at={message.created_at}, 数据库自增ID={message.id}"
        )

        emit('message_sent', {
            'message_id': message_data['id'],
            'wechat_id': wechat_id,
            'contact_id': target_wechat_id,
            'status': 'sent',
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"通过WebSocket发送直接消息: 用户={user_id}, 微信ID={wechat_id}, 联系人={target_wechat_id}")

    except Exception as e:
        logger.error(f"WebSocket发送直接消息失败: {str(e)}", exc_info=True)
        db.rollback()
        emit('error', {'message': f'发送消息失败: {str(e)}'})
    finally:
        if 'db' in locals():
            db.close()



@socketio.on('reconnect')
def handle_reconnect(data):
    """处理重连请求，补发未确认消息"""
    db = None
    try:
        user_id = data.get('user_id')
        last_ack_id = data.get('last_ack_id')

        if not user_id:
            emit('error', {'message': '重连请求缺少user_id'})
            return

        if user_id not in user_socket_map:
            emit('error', {'message': '用户未认证', 'code': 'auth_required'})
            return

        # ✅ 所有前置检查通过后才连接数据库
        db = next(get_db())

        query = db.query(WechatMessage).filter(
            WechatMessage.ack_status == 'pending'
        )

        if last_ack_id:
            last_message = db.query(WechatMessage).filter(WechatMessage.message_id == last_ack_id).first()
            if last_message:
                query = query.filter(WechatMessage.id > last_message.id)

        unacked_messages = query.order_by(WechatMessage.created_at.desc()).limit(100).all()

        contact_ids = {msg.contact_id for msg in unacked_messages}
        contacts = {
            contact.id: contact
            for contact in db.query(WechatContact).filter(WechatContact.id.in_(contact_ids)).all()
        }

        resent_count = 0
        for message in unacked_messages:
            contact = contacts.get(message.contact_id)
            if contact and getattr(contact, 'owner', None) and contact.owner.user_id == user_id:
                message_data = {
                    'id': message.message_id,
                    "type": "message",
                    'wechat_id': contact.wechat_id,
                    'contact_id': contact.wechat_id,
                    'content': message.content,
                    'content_type': message.content_type,
                    'created_at': message.created_at.isoformat(),
                    'require_ack': True,
                    'send_type': 'active' if message.sender_id == user_id else 'passive'
                }

                add_message_to_queue(user_id, message_data)
                resent_count += 1

        emit('reconnect_complete', {
            'status': 'ok',
            'resent_count': resent_count,
            'timestamp': datetime.now().isoformat()
        })
        logger.info(f"用户 {user_id} 重连完成，补发 {resent_count} 条未确认消息")
    except Exception as e:
        logger.error(f"处理重连请求失败: {str(e)}", exc_info=True)
        emit('error', {'message': f'重连失败: {str(e)}'})
    finally:
        if db:
            db.close()



def process_message_queue(user_id):
    """处理用户消息队列"""
    if user_id not in user_message_queues or not user_message_queues[user_id]:
        return

    if user_id not in user_socket_map:
        logger.warning(f"用户 {user_id} 不在线，无法处理消息队列")
        return

    sid = user_socket_map[user_id]

    messages_to_send = user_message_queues[user_id][:5]

    for message in messages_to_send:
        try:
            if 'id' not in message:
                message['id'] = f"{user_id}_{int(time.time() * 1000)}_{hash(str(message))}"

            socketio.emit('new_message', message, to=sid)
            logger.debug(f"向用户 {user_id} 发送队列消息: {message.get('id')}")

        except Exception as e:
            logger.error(f"发送队列消息失败: {str(e)}")


def add_message_to_queue(user_id, message):
    """添加消息到用户队列"""
    if user_id not in user_message_queues:
        user_message_queues[user_id] = []

    if 'id' not in message:
        message['id'] = f"{user_id}_{int(time.time() * 1000)}_{hash(str(message))}"

    user_message_queues[user_id].append(message)

    if user_id in user_socket_map:
        process_message_queue(user_id)
    else:
        logger.info(f"用户 {user_id} 不在线，消息已加入队列")


app.add_message_to_queue = add_message_to_queue


def cleanup_expired_connections():
    """清理过期连接和消息队列"""
    try:
        now = datetime.now()
        expired_users = []

        for user_id, last_heartbeat in user_last_heartbeat.items():
            if (now - last_heartbeat).total_seconds() > 300:  # 5分钟超时
                expired_users.append(user_id)

        for user_id in expired_users:
            if user_id in user_socket_map:
                sid = user_socket_map.pop(user_id)
                logger.info(f"清理过期连接: 用户={user_id}, SID={sid}")

            if user_id in user_last_heartbeat:
                user_last_heartbeat.pop(user_id)

            if user_id in user_message_queues and len(user_message_queues[user_id]) > 100:
                user_message_queues[user_id] = user_message_queues[user_id][-100:]
                logger.info(f"清理过大的消息队列: 用户={user_id}, 保留最新100条消息")

        logger.debug(f"当前活跃连接数: {len(user_socket_map)}, 消息队列数: {len(user_message_queues)}")
    except Exception as e:
        logger.error(f"清理过期连接失败: {str(e)}")


import threading


def start_cleanup_task():
    """启动定时清理任务"""
    cleanup_expired_connections()
    threading.Timer(300, start_cleanup_task).start()


start_cleanup_task()


@app.route('/api/keywords', methods=['GET'])
def get_keywords():
    """获取联系人关键词列表"""
    try:
        contact_id = request.args.get('contact_id')
        if not contact_id:
            return jsonify({"error": "缺少contact_id参数"}), 400

        db = next(get_db())
        keywords = db.query(KeywordFilter).filter(KeywordFilter.contact_id == contact_id).all()

        keyword_list = [
            {
                "id": keyword.id,
                "keyword": keyword.keyword,
                "replacement": keyword.replacement
            }
            for keyword in keywords
        ]

        return jsonify({"keywords": keyword_list})
    except Exception as e:
        logger.error(f"获取关键词列表失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/add_keyword', methods=['POST'])
def add_keyword():
    """添加关键词"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为JSON格式"}), 400

        contact_id = data.get("contact_id")
        keyword = data.get("keyword")
        replacement = data.get("replacement")

        if not contact_id or not keyword:
            return jsonify({"error": "缺少必要参数"}), 400

        db = next(get_db())
        contact = db.get(WechatContact, contact_id)

        if not contact:
            return jsonify({"error": "联系人不存在"}), 404

        new_keyword = KeywordFilter(
            contact_id=contact_id,
            keyword=keyword,
            replacement=replacement
        )

        db.add(new_keyword)
        db.commit()

        return jsonify({
            "success": True,
            "message": "关键词添加成功",
            "keyword_id": new_keyword.id
        })
    except Exception as e:
        logger.error(f"添加关键词失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/update_keyword', methods=['POST'])
def update_keyword():
    """更新关键词"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为JSON格式"}), 400

        keyword_id = data.get("keyword_id")
        keyword = data.get("keyword")
        replacement = data.get("replacement")

        if not keyword_id or not keyword:
            return jsonify({"error": "缺少必要参数"}), 400

        db = next(get_db())
        keyword_obj = db.get(KeywordFilter, keyword_id)

        if not keyword_obj:
            return jsonify({"error": "关键词不存在"}), 404

        keyword_obj.keyword = keyword
        keyword_obj.replacement = replacement

        db.commit()

        return jsonify({
            "success": True,
            "message": "关键词更新成功"
        })
    except Exception as e:
        logger.error(f"更新关键词失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/delete_keyword', methods=['POST'])
def delete_keyword():
    """删除关键词"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为JSON格式"}), 400

        keyword_id = data.get("keyword_id")

        if not keyword_id:
            return jsonify({"error": "缺少必要参数"}), 400

        db = next(get_db())
        keyword = db.get(KeywordFilter, keyword_id)

        if not keyword:
            return jsonify({"error": "关键词不存在"}), 404

        db.delete(keyword)
        db.commit()

        return jsonify({
            "success": True,
            "message": "关键词删除成功"
        })
    except Exception as e:
        logger.error(f"删除关键词失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/admin/contacts', methods=['GET'])
def admin_contacts():
    """管理员联系人管理页面"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = next(get_db())
    admin = db.query(User).filter(User.is_admin == True).first()

    return render_template(
        'admin_contacts.html',
        user=admin
    )


@app.route('/user/contacts', methods=['GET'])
def user_contacts():
    """用户联系人管理页面"""
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('user_login'))

        return render_template(
            'user_contacts.html',
            user=user
        )
    finally:
        db.close()


@app.route('/api/wechat_accounts', methods=['GET'])
def get_wechat_accounts():
    """获取用户的微信账号列表"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "缺少user_id参数"}), 400

        db = next(get_db())
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return jsonify({"error": "用户不存在"}), 404

        accounts = db.query(WechatContact).filter(
            WechatContact.owner_id == user.id,
            WechatContact.parent_id == None  # 只查询微信账号，不包括联系人
        ).all()

        account_list = [
            {
                "id": account.id,
                "wechat_id": account.wechat_id,
                "nickname": account.nickname,
                "avatar": account.avatar  # 添加了这一行
            }
            for account in accounts
        ]

        return jsonify({"accounts": account_list})
    except Exception as e:
        logger.error(f"获取微信账号列表失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/add_wechat_account', methods=['POST'])
def add_wechat_account():
    """添加微信账号"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为JSON格式"}), 400
        wechat_id = data.get("wechat_id")
        nickname = data.get("nickname")
        user_id = data.get("user_id")
        avatar_url = data.get("avatar_url")
        if not wechat_id or not nickname or not user_id:
            return jsonify({"error": "缺少必要参数"}), 400
        db = next(get_db())
        exist_account = db.query(WechatContact).filter(
            WechatContact.wechat_id == wechat_id,
            WechatContact.parent_id == None  # 确保是账号而不是联系人
        ).first()
        if exist_account:
            return jsonify({"error": "该微信账号已存在"}), 404
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        account = WechatContact(
            avatar=avatar_url,
            wechat_id=wechat_id,
            nickname=nickname,
            owner_id=user.id,
            parent_id=None,  # 明确设置为None表示这是一个微信账号
            is_group=False
        )
        db.add(account)
        db.commit()
        return jsonify({
            "success": True,
            "message": "成功添加微信账号"
        })
    except Exception as e:
        logger.error(f"添加微信账号失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/keyword_filters', methods=['GET'])
def get_keyword_filters():
    """获取关键词过滤列表"""
    try:
        contact_id = request.args.get('contact_id')
        if not contact_id:
            return jsonify({"error": "缺少contact_id参数"}), 400

        db = next(get_db())
        filters = db.query(KeywordFilter).filter(KeywordFilter.contact_id == contact_id).all()

        filter_list = [
            {
                "id": filter.id,
                "keyword": filter.keyword,
                "response": filter.response,
                "is_regex": filter.is_regex
            }
            for filter in filters
        ]

        return jsonify({"filters": filter_list})
    except Exception as e:
        logger.error(f"获取关键词过滤列表失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/add_keyword_filter', methods=['POST'])
def add_keyword_filter():
    """添加关键词过滤"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为JSON格式"}), 400

        contact_id = data.get("contact_id")
        keyword = data.get("keyword")
        response = data.get("response")
        is_regex = data.get("is_regex", False)

        if not contact_id or not keyword:
            return jsonify({"error": "缺少必要参数"}), 400

        db = next(get_db())

        contact = db.get(WechatContact, contact_id)
        if not contact:
            return jsonify({"error": "联系人不存在"}), 404

        keyword_filter = KeywordFilter(
            contact_id=contact_id,
            keyword=keyword,
            response=response,
            is_regex=is_regex
        )
        db.add(keyword_filter)
        db.commit()

        return jsonify({
            "success": True,
            "id": keyword_filter.id,
            "message": "成功添加关键词过滤"
        })
    except Exception as e:
        logger.error(f"添加关键词过滤失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/delete_keyword_filter/<int:filter_id>', methods=['DELETE'])
def delete_keyword_filter(filter_id):
    """删除关键词过滤"""
    try:
        db = next(get_db())

        keyword_filter = db.get(KeywordFilter, filter_id)
        if not keyword_filter:
            return jsonify({"error": "关键词过滤不存在"}), 404

        db.delete(keyword_filter)
        db.commit()

        return jsonify({
            "success": True,
            "message": "成功删除关键词过滤"
        })
    except Exception as e:
        logger.error(f"删除关键词过滤失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/ai_strategies', methods=['GET'])
def get_ai_strategies():
    """获取AI策略列表"""
    try:
        db = next(get_db())
        strategies = db.query(AIStrategy).all()

        strategy_list = [
            {
                "id": strategy.id,
                "name": strategy.name,
                "description": strategy.description,
                "prompt_template": strategy.prompt_template,
                "system_message": strategy.system_message,
                "temperature": strategy.temperature,
                "max_tokens": strategy.max_tokens
            }
            for strategy in strategies
        ]

        return jsonify({"strategies": strategy_list})
    except Exception as e:
        logger.error(f"获取AI策略列表失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/add_ai_strategy', methods=['POST'])
def add_ai_strategy():
    """添加AI策略"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为JSON格式"}), 400

        name = data.get("name")
        description = data.get("description")
        prompt_template = data.get("prompt_template")
        system_message = data.get("system_message")
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens", 2000)

        if not name or not prompt_template:
            return jsonify({"error": "缺少必要参数"}), 400

        db = next(get_db())

        existing = db.query(AIStrategy).filter(AIStrategy.name == name).first()
        if existing:
            return jsonify({"error": "策略名称已存在"}), 400

        strategy = AIStrategy(
            name=name,
            description=description,
            prompt_template=prompt_template,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens
        )
        db.add(strategy)
        db.commit()

        return jsonify({
            "success": True,
            "id": strategy.id,
            "message": "成功添加AI策略"
        })
    except Exception as e:
        logger.error(f"添加AI策略失败: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500


@app.route('/api/websocket_config', methods=['GET'])
def get_websocket_config():
    """获取WebSocket配置状态"""
    return jsonify({
        "enabled": ENABLE_SOCKET_IO,  # 直接使用配置变量
        "server_url": request.host_url.rstrip('/')
    })



@app.route('/user/moments')
def user_moments():
    """用户朋友圈管理页面"""
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return redirect(url_for('user_login'))

        page = request.args.get('page', 1, type=int)
        per_page = 10
        wechat_filter = request.args.get('wechat_id', '')

        query = db.query(Moment).filter(Moment.owner_id == user.id)
        if wechat_filter:
            query = query.filter(Moment.wechat_id == wechat_filter)

        total = query.count()
        moments = query.order_by(Moment.created_time.desc()).offset((page - 1) * per_page).limit(per_page).all()

        wechat_accounts = db.query(WechatContact).filter(
            WechatContact.owner_id == user.id,
            WechatContact.parent_id == None
        ).all()

        total_pages = (total + per_page - 1) // per_page

        return render_template(
            'user_moments.html',
            user=user,
            moments=moments,
            wechat_accounts=wechat_accounts,
            page=page,
            total_pages=total_pages,
            wechat_filter=wechat_filter
        )
    finally:
        db.close()


@app.route('/user/moments/<int:moment_id>')
def user_moment_detail(moment_id):
    """朋友圈详情页"""
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return redirect(url_for('user_login'))

        moment = db.query(Moment).filter(
            Moment.id == moment_id,
            Moment.owner_id == user.id
        ).first()

        if not moment:
            return redirect(url_for('user_moments'))

        comments = db.query(MomentComment).filter(
            MomentComment.moment_id == moment_id
        ).order_by(MomentComment.created_time.asc()).all()

        return render_template(
            'user_moment_detail.html',
            user=user,
            moment=moment,
            comments=comments
        )
    finally:
        db.close()


@app.route('/api/moments', methods=['GET'])
def api_get_moments():
    """获取朋友圈列表API"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    try:
        user_id = session.get('user_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        wechat_id = request.args.get('wechat_id', '')

        db = next(get_db())
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        query = db.query(Moment).filter(Moment.owner_id == user.id)
        if wechat_id:
            query = query.filter(Moment.wechat_id == wechat_id)

        total = query.count()
        moments = query.order_by(Moment.created_time.desc()).offset((page - 1) * per_page).limit(per_page).all()

        moments_data = []
        for moment in moments:
            media_urls = moment.media_urls
            if isinstance(media_urls, str):
                try:
                    media_urls = json.loads(media_urls)
                except:
                    media_urls = []
            elif media_urls is None:
                media_urls = []

            moments_data.append({
                'id': moment.id,
                'wechat_id': moment.wechat_id,
                'content': moment.content,
                'media_urls': media_urls,
                'created_time': moment.created_time.isoformat(),
                'like_count': moment.like_count,
                'comment_count': moment.comment_count
            })

        return jsonify({
            'moments': moments_data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"获取朋友圈列表失败: {str(e)}")
        return jsonify({'error': '服务器内部错误'}), 500


@app.route('/api/moments/<int:moment_id>/comments', methods=['GET', 'POST'])
def api_moment_comments(moment_id):
    """获取或添加朋友圈评论"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        moment = db.query(Moment).filter(
            Moment.id == moment_id,
            Moment.owner_id == user.id
        ).first()
        if not moment:
            return jsonify({'error': '朋友圈不存在'}), 404

        if request.method == 'GET':
            comments = db.query(MomentComment).filter(
                MomentComment.moment_id == moment_id
            ).order_by(MomentComment.created_time.asc()).all()

            comments_data = []
            for comment in comments:
                comments_data.append({
                    'id': comment.id,
                    'parent_id': comment.parent_id,
                    'wechat_id': comment.wechat_id,
                    'content': comment.content,
                    'created_time': comment.created_time.isoformat()
                })

            return jsonify({'comments': comments_data})

        elif request.method == 'POST':
            data = request.get_json()
            if not data or not data.get('content'):
                return jsonify({'error': '评论内容不能为空'}), 400

            comment = MomentComment(
                moment_id=moment_id,
                parent_id=data.get('parent_id'),
                wechat_id=data.get('wechat_id', user.user_id),
                content=data['content']
            )
            db.add(comment)

            moment.comment_count = db.query(MomentComment).filter(
                MomentComment.moment_id == moment_id
            ).count() + 1

            db.commit()

            return jsonify({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'parent_id': comment.parent_id,
                    'wechat_id': comment.wechat_id,
                    'content': comment.content,
                    'created_time': comment.created_time.isoformat()
                }
            })
    except Exception as e:
        logger.error(f"处理朋友圈评论失败: {str(e)}")
        return jsonify({'error': '服务器内部错误'}), 500
    finally:
        db.close()


@app.route('/api/moments/<int:moment_id>/comments/<int:comment_id>', methods=['DELETE'])
def api_delete_comment(moment_id, comment_id):
    """删除朋友圈评论"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        moment = db.query(Moment).filter(
            Moment.id == moment_id,
            Moment.owner_id == user.id
        ).first()
        if not moment:
            return jsonify({'error': '朋友圈不存在'}), 404

        comment = db.query(MomentComment).filter(
            MomentComment.id == comment_id,
            MomentComment.moment_id == moment_id
        ).first()
        if not comment:
            return jsonify({'error': '评论不存在'}), 404

        db.delete(comment)

        moment.comment_count = db.query(MomentComment).filter(
            MomentComment.moment_id == moment_id
        ).count() - 1

        db.commit()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"删除朋友圈评论失败: {str(e)}")
        return jsonify({'error': '服务器内部错误'}), 500
    finally:
        db.close()


@app.route('/api/moments/<int:moment_id>', methods=['DELETE'])
def api_delete_moment(moment_id):
    """删除朋友圈"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        moment = db.query(Moment).filter(
            Moment.id == moment_id,
            Moment.owner_id == user.id
        ).first()
        if not moment:
            return jsonify({'error': '朋友圈不存在'}), 404

        db.delete(moment)
        db.commit()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"删除朋友圈失败: {str(e)}")
        return jsonify({'error': '服务器内部错误'}), 500
    finally:
        db.close()


if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)

    initialize_database()

    try:
        from config import load_config_from_file
        load_config_from_file()
        logger.info("已从配置文件加载保存的设置")
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")

@app.route('/admin/customer-profiling')
@admin_required
def admin_customer_profiling():
    db = next(get_db())
    try:
        total_customers = db.query(User).filter(User.is_admin == False).count()
        high_value_customers = db.query(User).filter(
            User.is_admin == False,
            User.value_level == '高价值'
        ).count()
        active_customers = db.query(User).filter(
            User.is_admin == False,
            User.activity_score >= 60
        ).count()
        
        avg_activity = db.query(func.avg(User.activity_score)).filter(
            User.is_admin == False
        ).scalar() or 0
        
        customers = db.query(User).filter(User.is_admin == False).all()
        
        return render_template('admin_customer_profiling.html',
                             total_customers=total_customers,
                             high_value_customers=high_value_customers,
                             active_customers=active_customers,
                             avg_activity_score=round(avg_activity, 1),
                             customers=customers)
    finally:
        db.close()

@app.route('/admin/intent-statistics')
@admin_required
def admin_intent_statistics():
    db = next(get_db())
    try:
        intent_stats = {}
        intent_trends = {}
        
        for intent_type in ['高意向', '一般意向', '沉默', '已成交']:
            count = db.query(IntentTracking).filter(
                IntentTracking.intent_type == intent_type
            ).count()
            intent_stats[intent_type] = count
            
            yesterday_count = db.query(IntentTracking).filter(
                IntentTracking.intent_type == intent_type,
                IntentTracking.detected_at >= datetime.now() - timedelta(days=1)
            ).count()
            intent_trends[intent_type] = yesterday_count
        
        intent_changes = db.query(IntentTracking).order_by(
            IntentTracking.detected_at.desc()
        ).limit(50).all()
        
        trend_labels = ['今日', '昨日', '前日', '3日前', '4日前', '5日前', '6日前']
        trend_data = {
            '高意向': [10, 8, 12, 6, 9, 7, 5],
            '一般意向': [15, 12, 18, 10, 14, 11, 8],
            '已成交': [3, 2, 4, 1, 2, 3, 1]
        }
        
        return render_template('admin_intent_statistics.html',
                             intent_stats=intent_stats,
                             intent_trends=intent_trends,
                             intent_changes=intent_changes,
                             trend_labels=json.dumps(trend_labels),
                             trend_data=trend_data,
                             intent_config=INTENT_LEVELS)
    finally:
        db.close()

@app.route('/admin/proactive-tracking')
@admin_required
def admin_proactive_tracking():
    db = next(get_db())
    try:
        tracking_stats = {
            'enabled_count': db.query(WechatContact).filter(
                WechatContact.auto_follow_enabled == True
            ).count(),
            'today_sent': db.query(ProactiveMessage).filter(
                ProactiveMessage.sent_time >= datetime.now().date()
            ).count(),
            'response_rate': 75.5,
            'pending_count': db.query(ProactiveMessage).filter(
                ProactiveMessage.status == 'pending'
            ).count()
        }
        
        message_templates = [
            {'id': 1, 'name': '关怀问候', 'scenario': '关怀', 'content': '您好{name}，最近怎么样？', 'usage_count': 25},
            {'id': 2, 'name': '产品推荐', 'scenario': '营销', 'content': 'Hi {name}，我们有新产品推荐', 'usage_count': 18}
        ]
        
        proactive_messages = db.query(ProactiveMessage).order_by(
            ProactiveMessage.created_at.desc()
        ).limit(50).all()
        
        return render_template('admin_proactive_tracking.html',
                             tracking_stats=tracking_stats,
                             message_templates=message_templates,
                             proactive_messages=proactive_messages,
                             global_config=PROACTIVE_FOLLOW_CONFIG)
    finally:
        db.close()

@app.route('/user/customer-management')
@user_required
def user_customer_management():
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        contacts = db.query(WechatContact).filter(
            WechatContact.owner_id == user.id
        ).all()
        
        total_customers = len(contacts)
        high_intent_customers = 0
        active_customers = 0
        deal_customers = 0
        
        for contact in contacts:
            latest_intent = db.query(IntentTracking).filter(
                IntentTracking.contact_id == contact.id
            ).order_by(IntentTracking.detected_at.desc()).first()
            
            if latest_intent:
                contact.latest_intent = latest_intent.intent_type
                if latest_intent.intent_type == '高意向':
                    high_intent_customers += 1
                elif latest_intent.intent_type == '已成交':
                    deal_customers += 1
            
            if contact.last_active_at and contact.last_active_at >= datetime.now() - timedelta(days=7):
                active_customers += 1
            
            contact.tags = []
        
        return render_template('user_customer_management.html',
                             contacts=contacts,
                             total_customers=total_customers,
                             high_intent_customers=high_intent_customers,
                             active_customers=active_customers,
                             deal_customers=deal_customers)
    finally:
        db.close()

@app.route('/admin/api/customer/<int:customer_id>', methods=['GET'])
@admin_required
def get_customer_api(customer_id):
    db = next(get_db())
    try:
        customer = db.query(User).filter(User.id == customer_id).first()
        if not customer:
            return jsonify({'success': False, 'message': '客户不存在'})
        
        return jsonify({
            'success': True,
            'value_level': customer.value_level,
            'activity_score': customer.activity_score,
            'profile_desc': customer.profile_desc,
            'tags': customer.tags
        })
    finally:
        db.close()

@app.route('/admin/api/customer/<int:customer_id>', methods=['PUT'])
@admin_required
def update_customer_api(customer_id):
    db = next(get_db())
    try:
        customer = db.query(User).filter(User.id == customer_id).first()
        if not customer:
            return jsonify({'success': False, 'message': '客户不存在'})
        
        data = request.get_json()
        customer.value_level = data.get('value_level', customer.value_level)
        customer.activity_score = data.get('activity_score', customer.activity_score)
        customer.profile_desc = data.get('profile_desc', customer.profile_desc)
        
        if 'tags' in data and data['tags']:
            tags_list = [tag.strip() for tag in data['tags'].split(',') if tag.strip()]
            tags_data = [{'tag': tag, 'source': '人工', 'created_at': datetime.now().isoformat()} for tag in tags_list]
            customer.tags = json.dumps(tags_data, ensure_ascii=False)
            customer.tag_source = '人工'
        
        db.commit()
        
        log = OperationLog(
            user_id=None,
            operation_type='客户画像编辑',
            operation_desc=f'编辑客户 {customer.username} 的画像信息',
            target_type='User',
            target_id=str(customer_id)
        )
        db.add(log)
        db.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"更新客户信息失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/user/api/contact/<int:contact_id>/auto-follow', methods=['POST'])
@user_required
def toggle_auto_follow_api(contact_id):
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        contact = db.query(WechatContact).filter(
            WechatContact.id == contact_id,
            WechatContact.owner_id == user.id
        ).first()
        
        if not contact:
            return jsonify({'success': False, 'message': '联系人不存在'})
        
        data = request.get_json()
        contact.auto_follow_enabled = data.get('enabled', False)
        db.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"设置自动跟踪失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/user/api/contact/<int:contact_id>', methods=['GET'])
@user_required
def get_contact_info_api(contact_id):
    """获取客户详细信息API"""
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        contact = db.query(WechatContact).filter(
            WechatContact.id == contact_id,
            WechatContact.owner_id == user.id
        ).first()
        
        if not contact:
            return jsonify({'success': False, 'message': '联系人不存在'})
        
        tags = []
        if contact.tags:
            try:
                import json
                tags = json.loads(contact.tags) if isinstance(contact.tags, str) else contact.tags
            except:
                tags = []
        
        latest_intent = db.query(IntentTracking).filter(
            IntentTracking.contact_id == contact.id
        ).order_by(IntentTracking.detected_at.desc()).first()
        
        return jsonify({
            'success': True,
            'id': contact.id,
            'wechat_id': contact.wechat_id,
            'nickname': contact.nickname,
            'remark': contact.remark,
            'tags': tags,
            'customer_type': contact.customer_type or '潜在客户',
            'follow_frequency': contact.follow_frequency or 'weekly',
            'auto_follow_enabled': contact.auto_follow_enabled or False,
            'ai_reply_enabled': contact.ai_reply_enabled or False,
            'intent_type': latest_intent.intent_type if latest_intent else '未知',
            'last_active_at': contact.last_active_at.isoformat() if contact.last_active_at else None,
            'created_at': contact.created_at.isoformat() if contact.created_at else None
        })
    except Exception as e:
        logger.error(f"获取客户信息失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/user/api/contact/<int:contact_id>/tags', methods=['PUT'])
@user_required
def update_contact_tags_api(contact_id):
    """更新客户标签API"""
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        contact = db.query(WechatContact).filter(
            WechatContact.id == contact_id,
            WechatContact.owner_id == user.id
        ).first()
        
        if not contact:
            return jsonify({'success': False, 'message': '联系人不存在'})
        
        data = request.get_json()
        
        tags_str = data.get('tags', '')
        if tags_str:
            tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            import json
            contact.tags = json.dumps(tags_list, ensure_ascii=False)
        else:
            contact.tags = '[]'
        
        if 'customer_type' in data:
            contact.customer_type = data['customer_type']
        if 'follow_frequency' in data:
            contact.follow_frequency = data['follow_frequency']
        
        db.commit()
        
        from database import OperationLog
        log = OperationLog(
            user_id=user.id,
            operation_type='标签管理',
            operation_desc=f'更新客户 {contact.nickname or contact.wechat_id} 的标签和信息',
            target_type='contact',
            target_id=str(contact.id),
            ip_address=request.remote_addr
        )
        db.add(log)
        db.commit()
        
        return jsonify({'success': True, 'message': '更新成功'})
    except Exception as e:
        logger.error(f"更新客户标签失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/user/api/contacts/batch-tags', methods=['POST'])
@user_required
def batch_update_tags_api():
    """批量更新客户标签API"""
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        data = request.get_json()
        contact_ids = data.get('contact_ids', [])
        action = data.get('action', 'add')  # add, remove, replace
        tags_str = data.get('tags', '')
        
        if not contact_ids:
            return jsonify({'success': False, 'message': '请选择要操作的客户'})
        
        if not tags_str:
            return jsonify({'success': False, 'message': '请输入标签'})
        
        new_tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        updated_count = 0
        
        for contact_id in contact_ids:
            contact = db.query(WechatContact).filter(
                WechatContact.id == contact_id,
                WechatContact.owner_id == user.id
            ).first()
            
            if not contact:
                continue
            
            existing_tags = []
            if contact.tags:
                try:
                    import json
                    existing_tags = json.loads(contact.tags) if isinstance(contact.tags, str) else contact.tags
                except:
                    existing_tags = []
            
            if action == 'add':
                final_tags = list(set(existing_tags + new_tags))
            elif action == 'remove':
                final_tags = [tag for tag in existing_tags if tag not in new_tags]
            else:  # replace
                final_tags = new_tags
            
            import json
            contact.tags = json.dumps(final_tags, ensure_ascii=False)
            updated_count += 1
        
        db.commit()
        
        from database import OperationLog
        log = OperationLog(
            user_id=user.id,
            operation_type='批量标签管理',
            operation_desc=f'批量{action}标签: {tags_str}，影响 {updated_count} 个客户',
            target_type='contacts',
            target_id=','.join(map(str, contact_ids)),
            ip_address=request.remote_addr
        )
        db.add(log)
        db.commit()
        
        return jsonify({'success': True, 'message': f'成功更新 {updated_count} 个客户的标签'})
    except Exception as e:
        logger.error(f"批量更新标签失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/user/api/contact/<int:contact_id>/send-message', methods=['POST'])
@user_required
def send_message_to_contact_api(contact_id):
    """发送消息给客户API"""
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        contact = db.query(WechatContact).filter(
            WechatContact.id == contact_id,
            WechatContact.owner_id == user.id
        ).first()
        
        if not contact:
            return jsonify({'success': False, 'message': '联系人不存在'})
        
        data = request.get_json()
        content = data.get('content', '').strip()
        send_time = data.get('send_time', 'now')
        scheduled_time = data.get('scheduled_time')
        
        if not content:
            return jsonify({'success': False, 'message': '消息内容不能为空'})
        
        from database import ProactiveMessage
        from datetime import datetime
        
        message = ProactiveMessage(
            contact_id=contact.id,
            message_type='手动发送',
            content=content,
            status='pending'
        )
        
        if send_time == 'scheduled' and scheduled_time:
            try:
                message.scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
            except:
                message.scheduled_time = None
        
        db.add(message)
        db.commit()
        
        if send_time == 'now':
            try:
                socketio.emit('send_message', {
                    'target_wechat_id': contact.wechat_id,
                    'content': content,
                    'message_id': message.id
                }, to=f'user_{user.user_id}')
                
                message.status = 'sent'
                message.sent_time = datetime.now()
                db.commit()
                
                from database import OperationLog
                log = OperationLog(
                    user_id=user.id,
                    operation_type='发送消息',
                    operation_desc=f'向客户 {contact.nickname or contact.wechat_id} 发送消息',
                    target_type='contact',
                    target_id=str(contact.id),
                    ip_address=request.remote_addr
                )
                db.add(log)
                db.commit()
                
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {str(e)}")
                message.status = 'failed'
                db.commit()
        
        return jsonify({'success': True, 'message': '消息发送成功' if send_time == 'now' else '消息已安排发送'})
    except Exception as e:
        logger.error(f"发送消息失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/user/contact/<int:contact_id>/profile')
@user_required
def user_contact_profile(contact_id):
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('user_login'))
        
        contact = db.query(WechatContact).filter(
            WechatContact.id == contact_id,
            WechatContact.owner_id == user.id
        ).first()
        
        if not contact:
            return render_template('error.html', 
                                 message='联系人不存在或无权访问',
                                 return_url=url_for('user_customer_management'))
        
        latest_intent = db.query(IntentTracking).filter(
            IntentTracking.contact_id == contact.id
        ).order_by(IntentTracking.detected_at.desc()).first()
        
        customer_profiles = db.query(CustomerProfile).filter(
            CustomerProfile.contact_id == contact.id
        ).all()
        
        recent_messages = db.query(WechatMessage).filter(
            WechatMessage.contact_id == contact.id
        ).order_by(WechatMessage.created_at.desc()).limit(10).all()
        
        proactive_messages = db.query(ProactiveMessage).filter(
            ProactiveMessage.contact_id == contact.id
        ).order_by(ProactiveMessage.created_at.desc()).limit(5).all()
        
        return render_template('user_contact_profile.html',
                             contact=contact,
                             latest_intent=latest_intent,
                             customer_profiles=customer_profiles,
                             recent_messages=recent_messages,
                             proactive_messages=proactive_messages)
    finally:
        db.close()

@app.route('/user/instruction_approval')
@user_required
def user_instruction_approval():
    """客户指令审批中心"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))
    
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            return redirect(url_for('user_login'))
        
        pending_messages = db.query(ProactiveMessage).filter(
            ProactiveMessage.status == 'pending'
        ).order_by(ProactiveMessage.created_at.desc()).all()
        
        return render_template('user_instruction_approval.html', 
                             user=user, 
                             pending_messages=pending_messages)
    finally:
        db.close()

@app.route('/user/approve_instruction/<int:message_id>', methods=['POST'])
@user_required
def approve_instruction(message_id):
    """批准指令"""
    db = next(get_db())
    try:
        message = db.query(ProactiveMessage).filter(
            ProactiveMessage.id == message_id
        ).first()
        
        if message:
            message.status = 'approved'
            db.commit()
            
            socketio.emit('send_message', {
                'contact_id': message.contact_id,
                'content': message.content,
                'message_type': message.message_type
            })
            
        return jsonify({'success': True})
    finally:
        db.close()

@app.route('/user/reject_instruction/<int:message_id>', methods=['POST'])
@user_required
def reject_instruction(message_id):
    """拒绝指令"""
    db = next(get_db())
    try:
        message = db.query(ProactiveMessage).filter(
            ProactiveMessage.id == message_id
        ).first()
        
        if message:
            message.status = 'rejected'
            db.commit()
            
        return jsonify({'success': True})
    finally:
        db.close()

@app.route('/user/knowledge_management')
@user_required
def user_knowledge_management():
    """客户知识库管理"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))
    
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            return redirect(url_for('user_login'))
        
        knowledge_records = db.query(AIFeedingRecord).filter(
            AIFeedingRecord.user_id == user.id
        ).order_by(AIFeedingRecord.created_at.desc()).all()
        
        return render_template('user_knowledge_management.html', 
                             user=user, 
                             knowledge_records=knowledge_records)
    finally:
        db.close()

@app.route('/user/add_knowledge', methods=['POST'])
@user_required
def add_knowledge():
    """添加知识库内容"""
    if not session.get('user_id'):
        return jsonify({'error': '未登录'}), 401
    
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        content = request.json.get('content')
        if not content:
            return jsonify({'error': '内容不能为空'}), 400
        
        knowledge_record = AIFeedingRecord(
            user_id=user.id,
            content=content,
            created_at=datetime.utcnow()
        )
        db.add(knowledge_record)
        db.commit()
        
        return jsonify({'success': True, 'message': '知识库内容添加成功'})
    finally:
        db.close()

@app.route('/user/data_analytics')
@user_required
def user_data_analytics():
    """客户数据统计与分析中心"""
    if not session.get('user_id'):
        return redirect(url_for('user_login'))
    
    db = next(get_db())
    try:
        user_id = session.get('user_id')
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            return redirect(url_for('user_login'))
        
        intent_stats = db.query(
            IntentTracking.intent_type,
            func.count(IntentTracking.id).label('count')
        ).group_by(IntentTracking.intent_type).all()
        
        user_type_stats = db.query(
            CustomerProfile.value_level,
            func.count(CustomerProfile.id).label('count')
        ).group_by(CustomerProfile.value_level).all()
        
        activity_stats = db.query(
            func.avg(CustomerProfile.activity_score).label('avg_score'),
            func.count(CustomerProfile.id).label('total_users')
        ).first()
        
        return render_template('user_data_analytics.html',
                             user=user,
                             intent_stats=intent_stats,
                             user_type_stats=user_type_stats,
                             activity_stats=activity_stats)
    finally:
        db.close()

@app.route('/api/user/intent_distribution')
@user_required
def get_intent_distribution():
    """获取意图分布数据API"""
    db = next(get_db())
    try:
        intent_stats = db.query(
            IntentTracking.intent_type,
            func.count(IntentTracking.id).label('count')
        ).group_by(IntentTracking.intent_type).all()
        
        data = {
            'labels': [stat.intent_type for stat in intent_stats],
            'data': [stat.count for stat in intent_stats]
        }
        
        return jsonify(data)
    finally:
        db.close()

if __name__ == "__main__":
    initialize_database()
    
    #register_api_messages(app)
    #register_api_send_message(app, socketio)
    
    from scheduled_tasks import initialize_scheduler
    initialize_scheduler(socketio)
    
    proactive_service = ProactiveMessagingService()
    
    #import eventlet
    #import eventlet.wsgi
    logger.info("以SocketIO方式启动，支持WebSocket")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False, log_output=True)

