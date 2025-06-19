import time
import hmac
import hashlib
from flask import request, jsonify
from functools import wraps
import logging
from config import IP_WHITELIST, IP_BLACKLIST, CONFIG

logger = logging.getLogger(__name__)

rate_limit_store = {}
ip_whitelist = IP_WHITELIST
ip_blacklist = IP_BLACKLIST

def load_ip_lists(whitelist_file=None, blacklist_file=None):
    """从文件加载IP白名单和黑名单"""
    global ip_whitelist, ip_blacklist
    
    if whitelist_file:
        try:
            with open(whitelist_file, 'r') as f:
                ip_whitelist = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"加载IP白名单失败: {str(e)}")
    
    if blacklist_file:
        try:
            with open(blacklist_file, 'r') as f:
                ip_blacklist = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"加载IP黑名单失败: {str(e)}")

# 移除直接导入的RATE_LIMIT_PER_MINUTE
# from config import RATE_LIMIT_PER_MINUTE

def rate_limit(requests_per_minute=None):
    """速率限制装饰器"""
    if requests_per_minute is None:
        # 从CONFIG字典中动态获取RATE_LIMIT_PER_MINUTE
        from config import CONFIG
        requests_per_minute = CONFIG.get('RATE_LIMIT_PER_MINUTE', 600)
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr
            
            if ip_blacklist and ip in ip_blacklist:
                logger.warning(f"拒绝访问：IP {ip} 在黑名单中")
                return jsonify({"error": "访问被拒绝"}), 403
            
            if ip_whitelist and ip not in ip_whitelist:
                logger.warning(f"拒绝访问：IP {ip} 不在白名单中")
                return jsonify({"error": "访问被拒绝"}), 403
            
            current_time = time.time()
            key = f"{ip}:{request.path}"
            
            if key in rate_limit_store:
                timestamps = rate_limit_store[key]
                timestamps = [ts for ts in timestamps if current_time - ts < 60]
                
                if len(timestamps) >= requests_per_minute:
                    logger.warning(f"速率限制：IP {ip} 请求过多")
                    return jsonify({"error": "请求过于频繁，请稍后再试"}), 429
                
                timestamps.append(current_time)
                rate_limit_store[key] = timestamps
            else:
                rate_limit_store[key] = [current_time]
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

def request_validation(required_fields):
    """请求参数验证装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if request.method == 'POST':
                data = request.get_json()
                if not data:
                    return jsonify({"error": "请求必须为 JSON 格式"}), 400
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({"error": f"缺少必要参数: {', '.join(missing_fields)}"}), 400
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

def get_app_secret(app_id):
    """获取应用密钥"""
    from config import CONFIG
    hmac_keys = CONFIG.get('HMAC_SECRET_KEYS', {})
    return hmac_keys.get(app_id)

def generate_hmac_signature(app_id, timestamp, nonce, body, app_secret):
    """生成HMAC签名"""
    sign_string = f"{app_id}{timestamp}{nonce}{body.decode('utf-8') if isinstance(body, bytes) else body}"
    signature = hmac.new(
        app_secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def hmac_signature_required(f):
    """HMAC签名验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        app_id = request.headers.get('X-App-ID')
        timestamp = request.headers.get('X-Timestamp')
        nonce = request.headers.get('X-Nonce')
        signature = request.headers.get('X-Signature')
        
        if not all([app_id, timestamp, nonce, signature]):
            logger.warning("HMAC验证失败: 缺少必要的头部信息")
            return jsonify({"error": "缺少必要的认证头部信息"}), 401
        
        try:
            current_time = int(time.time())
            request_time = int(timestamp)
            if abs(current_time - request_time) > CONFIG.get('HMAC_REQUEST_TIMEOUT', 300):
                logger.warning(f"HMAC验证失败: 请求已过期 - 时间差: {abs(current_time - request_time)}秒")
                return jsonify({"error": "请求已过期"}), 401
        except ValueError:
            logger.warning("HMAC验证失败: 时间戳格式无效")
            return jsonify({"error": "时间戳格式无效"}), 401
        
        app_secret = get_app_secret(app_id)
        if not app_secret:
            logger.warning(f"HMAC验证失败: 未知的AppID - {app_id}")
            return jsonify({"error": "无效的AppID"}), 401
        
        body = request.get_data()
        expected_signature = generate_hmac_signature(app_id, timestamp, nonce, body, app_secret)
        
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(f"HMAC验证失败: 签名不匹配 - AppID: {app_id}")
            return jsonify({"error": "签名验证失败"}), 401
        
        logger.info(f"HMAC验证成功 - AppID: {app_id}")
        return f(*args, **kwargs)
    return decorated_function
