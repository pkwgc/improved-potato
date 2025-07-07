from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, current_user
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import json
from werkzeug.security import generate_password_hash, check_password_hash

# 初始化 Flask 应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root123@localhost/tele_query'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True  # 美化 JSON 输出

# 初始化数据库
db = SQLAlchemy(app)

# 登录管理器
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class RechargeLog(db.Model):
    __tablename__ = "recharge_logs"
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 充值管理员
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)   # 被充值用户
    amount = db.Column(db.Float, nullable=False)                                  # 充值金额
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())      # 时间

    admin = db.relationship("User", foreign_keys=[admin_id])                     # 管理员关联
    user = db.relationship("User", foreign_keys=[user_id])                       # 被充值用户关联


# 用户模型
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)

# 查询日志模型
class QueryLog(db.Model):
    __tablename__ = "query_logs"
    __table_args__ = {'extend_existing': True}  # 添加这一行以避免重复定义错误

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    result = db.Column(db.Text)
    cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# 初始化数据库
with app.app_context():
    db.create_all()

# 登录用户加载
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/recharge/history")
def recharge_history():
    if 'user_id' not in session:
        return redirect(url_for("login"))

    logs = RechargeLog.query.order_by(RechargeLog.created_at.desc()).all()
    return render_template("recharge_history.html", logs=logs)

# 登录接口
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):  # ✅ 使用加密验证
            session['user_id'] = user.id
            return redirect(url_for("index"))
        flash("用户名或密码错误")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("请输入用户名和密码")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("用户名已存在")
            return redirect(url_for("register"))

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            balance=10.0  # 默认赠送余额
        )
        db.session.add(new_user)
        db.session.commit()
        flash("注册成功，请登录")
        return redirect(url_for("login"))

    return render_template("register.html")


# 注销接口
@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for("login"))

# 用户主页
@app.route("/")
def index():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    user = User.query.get(session['user_id'])
    logs = QueryLog.query.filter_by(user_id=user.id).order_by(QueryLog.created_at.desc()).limit(50).all()
    return render_template("index.html", user=user, logs=logs)


# 查询历史记录
@app.route("/history")
def history():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    user = User.query.get(session['user_id'])
    logs = QueryLog.query.filter_by(user_id=user.id).order_by(QueryLog.created_at.desc()).all()
    return render_template("history.html", logs=logs)

# 管理员充值页面
@app.route("/admin/recharge", methods=["GET", "POST"])
def admin_recharge():
    if 'user_id' not in session:
        return redirect(url_for("login"))

    user = User.query.get(session['user_id'])
    # 只允许管理员用户访问（建议使用 is_admin 字段）
    if not user.is_admin:  # 更优雅的方式是用字段而非硬编码 id=1
        flash("权限不足")
        return redirect(url_for("index"))

    users = User.query.all()

    if request.method == "POST":
        try:
            user_id = int(request.form.get("user_id"))
            amount = float(request.form.get("amount"))
            target_user = User.query.get(user_id)
            if not target_user:
                flash("用户不存在")
                return redirect(url_for("admin_recharge"))

            target_user.balance += amount

            # 添加充值记录
            log = RechargeLog(
                admin_id=user.id,
                user_id=target_user.id,
                amount=amount
            )
            db.session.add(log)
            db.session.commit()
            flash(f"已为 {target_user.username} 充值 {amount} 元")
            return redirect(url_for("admin_recharge"))
        except Exception as e:
            db.session.rollback()
            flash("充值失败，请重试")

    return render_template("admin_recharge.html", users=users)



# 远程 API 请求函数
def fetch_from_api(phone):
    url = "http://cd.gfggf.cn/ceshi.php"
    params = {"phone": phone, "type": "副号"}
    headers = {"User-Agent": "Mozilla/5.0"}

    with requests.Session() as session:
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        session.mount('http://', HTTPAdapter(max_retries=retries))

        try:
            r = session.get(url, headers=headers, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data.get("code") == 200:
                return {
                    "success": True,
                    "all_acc": data["data"].get("allAcc", "")
                }
            else:
                logging.error(f"API 业务错误: {data.get('msg')} (code={data.get('code')})")
                return {
                    "success": False,
                    "error": data.get("msg"),
                    "code": data.get("code")
                }
        except Exception as e:
            logging.error(f"请求失败: {str(e)}", exc_info=True)
            return {"success": False, "error": "远程接口失败"}

# 扣费函数
def deduct_balance(user, amount=1.0):
    if user.balance < amount:
        return False, "余额不足"
    user.balance -= amount
    db.session.commit()
    return True, "扣费成功"

# 查询接口
@app.route("/query")
def query_handler():
    if 'user_id' not in session:
        return jsonify({"code": 401, "msg": "请先登录"})

    phone = request.args.get("phone", "").strip()
    if not phone.isdigit() or len(phone) < 7 or len(phone) > 15:
        return render_template("query_result.html", error="请输入正确手机号（7~15位数字）", phone=phone)

    user = User.query.get(session['user_id'])

    api_response = fetch_from_api(phone)
    if not api_response.get("success"):
        return render_template("query_result.html", error=api_response.get("error", "远程接口失败"), phone=phone)

    success, msg = deduct_balance(user, amount=1.0)
    if not success:
        return render_template("query_result.html", error=msg, phone=phone)

    log = QueryLog(
        user_id=user.id,
        phone=phone,
        result=json.dumps(api_response),
        cost=1.0
    )
    db.session.add(log)
    db.session.commit()

    return render_template("query_result.html", phone=phone, result=api_response, balance=user.balance)



# 启动服务
if __name__ == "__main__":
    app.run(debug=False, host='127.0.0.1', port=8000)
