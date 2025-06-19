# login_module.py
from flask import request, jsonify
from datetime import datetime
import requests
import json
from functools import wraps
import time
from string_jiami import rsaenc, cocode
from models import db, User, RechargeRecord
from sqlalchemy import text

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip rate limiting in test environment
        if request.headers.get('X-Test-Request'):
            return f(*args, **kwargs)

        # Rate limiting logic for production
        now = time.time()
        key = f"{request.remote_addr}:{f.__name__}"

        # Allow 5 requests per second
        if hasattr(decorated_function, 'last_request_time') and \
           now - decorated_function.last_request_time < 0.2:
            return jsonify({"error": "Too many requests"}), 429

        decorated_function.last_request_time = now
        return f(*args, **kwargs)
    return decorated_function

def rechargesubmission():
    data = request.json
    phoneNum = data.get('phoneNum')  # 充值号码
    cardPwd = data.get('cardPwd')    # 充值卡密
    userid = data.get('userid')     # 用户ID

    # 检查 userid 是否存在，如果不存在，返回一个错误响应
    if userid is None:
        return jsonify({"error": "Missing userid"}), 400

    # 这里添加您的充值逻辑
    # ...

    # 返回一个 JSON 响应
    return jsonify({"message": "Recharge successful", "userid": userid}), 200

def kamichongz():
    #该程序转处理卡密充值流程
    return

@rate_limit
def login_route():
    data = request.json
    phoneNum = data.get('phoneNum')
    password = data.get('password')
    userid = data.get('userid')

    # Validate required fields
    if not all([userid, password, phoneNum]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Start a new transaction
        db.session.begin()

        # Get and lock the user row
        user = User.query.filter_by(userid=userid).with_for_update().first()

        if not user:
            db.session.rollback()
            return jsonify({"error": "User not found"}), 404

        # Debug logging for password validation
        print(f"Debug - User ID: {userid}")
        print(f"Debug - Stored Hash: {user.password_hash}")
        print(f"Debug - Input Password: {password}")

        if not user.check_password(password):
            db.session.rollback()
            return jsonify({"error": "Invalid password"}), 401

        # Check and update balance atomically
        if user.balance < 0.1:
            db.session.rollback()
            return jsonify({"error": "Insufficient balance"}), 400

        user.balance -= 0.1

        # Create transaction record
        record = RechargeRecord(
            userid=userid,
            phone_number=phoneNum,
            card_number="LOGIN",
            amount=0.1,
            status='success'
        )
        db.session.add(record)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Transaction failed: {str(e)}"}), 500

        return jsonify({
            "message": "Login successful",
            "balance": user.balance
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
