"""
Helper functions for WeChat AI Chatbot System
"""
import requests
import json
import re
from flask import request, Response
from urllib.parse import quote_plus

NEED_PROXY_PREFIX = [
    'http://shmmsns.qpic.cn',
    'https://shmmsns.qpic.cn',
    'http://thirdwx.qlogo.cn',
    'https://thirdwx.qlogo.cn',
]

def need_proxy(url):
    """Check if URL needs proxy"""
    return url and any(url.startswith(prefix) for prefix in NEED_PROXY_PREFIX)

def handle_proxy_request():
    """Handle proxy requests for images and other resources"""
    try:
        url = request.args.get('url')
        if not url:
            return "Missing URL parameter", 400
        
        if not need_proxy(url):
            return 'Forbidden', 403
            
        response = requests.get(url, timeout=10)
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        return Response(response.content, mimetype=content_type)
    except Exception as e:
        return f'Error: {e}', 500

def fix_invalid_backslashes(text):
    """Fix invalid backslashes in text"""
    return re.sub(r'(?<!\\)\\(?![\\/"bfnrtu])', r'\\\\', text)

def extract_reply_and_confidence(content):
    """从AI回复中提取回复内容、置信度和意图信息"""
    try:
        if not content:
            return "抱歉，我没有收到有效的回复。", 0.0, "no_intent", {}
        
        content = content.strip()
        
        if content.startswith('{') and content.endswith('}'):
            try:
                data = json.loads(content)
                reply = data.get('reply', content)
                confidence = float(data.get('confidence', 0.0))
                intent_type = data.get('intent_type', 'no_intent')
                intent_details = data.get('intent_details', {})
                return reply, confidence, intent_type, intent_details
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        return content, 0.5, "casual_chat", {}
        
    except Exception as e:
        return f"处理回复时出错: {str(e)}", 0.0, "error", {}

def register_template_filters(app):
    """Register custom template filters for Flask app"""
    
    @app.template_filter('proxy_url')
    def proxy_url_filter(url):
        if need_proxy(url):
            return f"/api/proxy?url={quote_plus(url)}"
        return url or ''

    @app.template_filter('from_json')
    def from_json_filter(value):
        """将JSON字符串转换为Python对象"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return value if value else []
