from functools import wraps
from flask import session, redirect, url_for, jsonify, request
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            if request.is_json:
                return jsonify({"error": "需要管理员权限"}), 401
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({"error": "需要用户登录"}), 401
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)
    return decorated_function
