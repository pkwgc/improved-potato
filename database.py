import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from urllib.parse import quote_plus
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, TOKEN_LIMIT_DEFAULT, HAS_APPOINTMENT_DEFAULT
import os
import logging

logger = logging.getLogger(__name__)

load_dotenv()

encoded_password = quote_plus(DB_PASSWORD)
import config
USE_SQLITE = config.USE_SQLITE

if USE_SQLITE:
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_system.db')
    DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    print(f"使用SQLite数据库: {db_path}")
else:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_recycle=3600,  # 在连接被服务器关闭之前回收它（秒）
            pool_pre_ping=True,  # 在使用连接前先ping一下，确保连接有效
            pool_size=10,        # 连接池大小
            max_overflow=20      # 允许的最大连接数
        )
    except Exception as e:
        logger.warning(f"无法连接到MySQL数据库: {str(e)}")
        logger.warning("回退到SQLite数据库")
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_system.db')
        DATABASE_URL = f"sqlite:///{db_path}"
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True)  # 微信ID
    username = Column(String(50), index=True)  # 显示名称
    password = Column(String(255), nullable=True)  # 用户密码（哈希后）
    is_admin = Column(Boolean, default=False)
    token_limit = Column(Integer, default=0)  # 0表示无限制
    token_balance = Column(Integer, default=0)  # 剩余可用token数量
    token_package = Column(String(50), nullable=True)  # 套餐包类型
    has_appointment = Column(Boolean, default=False)  # 是否有预约
    identity = Column(String(200), nullable=True)  # 用户身份信息
    hobbies = Column(String(500), nullable=True)  # 用户爱好信息
    profile_data = Column(Text, nullable=True)  # 存储其他JSON格式的用户资料数据
    
    real_name = Column(String(100), default='')  # 真实姓名
    id_number = Column(String(20), default='')   # 身份证号
    phone = Column(String(20), default='')       # 手机号
    email = Column(String(100), default='')      # 邮箱
    
    tags = Column(Text, nullable=True)  # JSON格式存储标签
    value_level = Column(String(20), default='普通')  # 价值等级：高价值、中价值、普通、低价值
    activity_score = Column(Float, default=0.0)  # 活跃度评分 0-100
    last_active_time = Column(DateTime, nullable=True)  # 最近互动时间
    order_amount_total = Column(Float, default=0.0)  # 历史订单总金额
    conversion_rate = Column(Float, default=0.0)  # 转化概率 0-1
    profile_desc = Column(Text, nullable=True)  # 画像说明
    tag_source = Column(String(20), default='AI')  # 标签来源：AI/人工
    
    max_wechat_accounts = Column(Integer, default=1)  # 最大微信账号绑定数
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    contexts = relationship("Context", back_populates="user")
    billing_records = relationship("BillingRecord", back_populates="user")
    inventory_uploads = relationship("InventoryUpload", back_populates="user")
    package_purchases = relationship("TokenPackagePurchase", back_populates="user")

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    industry_id = Column(Integer, ForeignKey("industries.id"), nullable=True)
    content = Column(Text)
    template_type = Column(String(20), default="chat", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    industry = relationship("Industry", back_populates="templates")
    bindings = relationship("UserTemplateBinding", back_populates="template")

class UserTemplateBinding(Base):
    __tablename__ = "user_template_bindings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    template_id = Column(Integer, ForeignKey("templates.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")
    template = relationship("Template", back_populates="bindings")

class Context(Base):
    __tablename__ = "contexts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    template_id = Column(Integer, ForeignKey("templates.id"))
    context_data = Column(Text)  # 存储JSON格式的上下文数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="contexts")
    template = relationship("Template")
    messages = relationship("ChatMessage", back_populates="context")

class BillingRecord(Base):
    __tablename__ = "billing_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String(50), nullable=True)  # 添加用户名字段
    tokens_used = Column(Integer, default=0)  # Token计费
    duration_seconds = Column(Float, default=0.0)  # 时间计费（秒）
    cost = Column(Float, default=0.0)  # 费用
    template_name = Column(String(50), nullable=True)  # 添加模板名称字段
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="billing_records")

class AIFeedingRecord(Base):
    __tablename__ = "ai_feeding_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)  # 投喂内容
    feedback = Column(Text, nullable=True)  # 用户反馈
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")

class Industry(Base):
    __tablename__ = "industries"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    templates = relationship("Template", back_populates="industry")
    intents = relationship("Intent", back_populates="industry")

class Intent(Base):
    __tablename__ = "intents"
    
    id = Column(Integer, primary_key=True, index=True)
    industry_id = Column(Integer, ForeignKey("industries.id"))
    name = Column(String(50), index=True)
    description = Column(Text, nullable=True)
    api_endpoint = Column(String(255), nullable=True)
    parameters = Column(Text, nullable=True)  # JSON格式参数定义
    created_at = Column(DateTime, default=datetime.utcnow)
    
    industry = relationship("Industry", back_populates="intents")

def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.warning(f"无法创建数据库表: {str(e)}")
        logger.warning("这是正常的，如果您在没有MySQL服务器的环境中运行。将使用SQLite内存数据库进行测试。")

def get_db():
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.warning(f"无法连接到数据库: {str(e)}")
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        test_engine = create_engine('sqlite:///:memory:')
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        
        Base.metadata.create_all(bind=test_engine)
        
        test_db = TestingSessionLocal()
        yield test_db
    finally:
        try:
            db.close()
        except:
            pass

def load_context_from_db(db, user_id, template_name):
    """从数据库加载上下文"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.warning(f"加载上下文失败: 用户不存在 (user_id={user_id})")
        return []
    
    template = db.query(Template).filter(Template.name == template_name).first()
    if not template:
        logger.warning(f"加载上下文失败: 模板不存在 (template_name={template_name})")
        return []
    
    context = db.query(Context).filter(
        Context.user_id == user.id,
        Context.template_id == template.id
    ).first()
    
    if not context:
        logger.info(f"用户 {user_id} 没有与模板 {template_name} 相关的上下文，返回空列表")
        return []
    
    try:
        context_data = json.loads(context.context_data)
        logger.info(f"成功加载上下文: 用户={user_id}, 模板={template_name}, 消息数={len(context_data)}")
        return context_data
    except json.JSONDecodeError as e:
        logger.error(f"上下文JSON解析失败: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"加载上下文时出错: {str(e)}")
        return []

def save_context_to_db(db, user_id, template_name, context_data, username=None):
    """保存上下文到数据库，返回Context对象"""
    if not user_id:
        logger.error("保存上下文失败: user_id为空")
        return False
        
    user_id = user_id.strip() if isinstance(user_id, str) else user_id
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.info(f"创建新用户: user_id={user_id}, username={username}")
        user = User(user_id=user_id, username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    template = db.query(Template).filter(Template.name == template_name).first()
    if not template:
        logger.error(f"保存上下文失败: 模板不存在 (template_name={template_name})")
        return False
    
    context = db.query(Context).filter(
        Context.user_id == user.id,
        Context.template_id == template.id
    ).first()
    
    try:
        context_json = json.dumps(context_data, ensure_ascii=False)
        
        if not context:
            logger.info(f"创建新上下文: user_id={user_id}, template={template_name}")
            context = Context(
                user_id=user.id,
                template_id=template.id,
                context_data=context_json
            )
            db.add(context)
        else:
            logger.info(f"更新现有上下文: user_id={user_id}, template={template_name}")
            context.context_data = context_json
            context.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(context)
        
        from config import ENABLE_JSON_STORAGE, CHAT_STORAGE_DIR
        if ENABLE_JSON_STORAGE:
            try:
                from chat_storage import ChatStorage
                chat_storage = ChatStorage(CHAT_STORAGE_DIR)
                chat_storage.save_context(user.user_id, context.id, context_data)
                logger.info(f"上下文已同步保存到JSON文件: user_id={user_id}, context_id={context.id}")
            except Exception as e:
                logger.error(f"保存上下文到JSON失败: {str(e)}")
        
        return context
    except Exception as e:
        logger.error(f"保存上下文到数据库失败: {str(e)}")
        db.rollback()
        return False

def get_bound_template_from_db(db, user_id):
    """从数据库获取用户绑定的模板"""
    if not user_id:
        logger.error("获取绑定模板失败: user_id为空")
        return None
        
    user_id = user_id.strip() if isinstance(user_id, str) else user_id
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = db.query(User).filter(User.username == user_id).first()
        if not user:
            logger.warning(f"获取绑定模板失败: 用户不存在 (user_id={user_id})")
            return None
    
    binding = db.query(UserTemplateBinding).filter(
        UserTemplateBinding.user_id == user.id
    ).order_by(UserTemplateBinding.updated_at.desc()).first()
    
    if not binding:
        logger.warning(f"用户 {user_id} 没有绑定任何模板")
        return None
    
    template = db.query(Template).filter(Template.id == binding.template_id).first()
    if not template:
        logger.warning(f"用户 {user_id} 绑定的模板ID {binding.template_id} 不存在")
        return None
    
    logger.info(f"用户 {user_id} 绑定的模板: {template.name}")
    return template.name

def bind_template_to_db(db, user_id, template_name, username=None):
    """在数据库中绑定用户和模板"""
    if not user_id:
        logger.error("绑定模板失败: user_id为空")
        return False
        
    user_id = user_id.strip() if isinstance(user_id, str) else user_id
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.info(f"创建新用户并绑定模板: user_id={user_id}, username={username}, template={template_name}")
        user = User(user_id=user_id, username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    template = db.query(Template).filter(Template.name == template_name).first()
    if not template:
        logger.error(f"绑定模板失败: 模板不存在 (template_name={template_name})")
        return False
    
    binding = db.query(UserTemplateBinding).filter(
        UserTemplateBinding.user_id == user.id,
        UserTemplateBinding.template_id == template.id
    ).first()
    
    if not binding:
        logger.info(f"创建新绑定: user_id={user_id}, template={template_name}")
        binding = UserTemplateBinding(
            user_id=user.id,
            template_id=template.id
        )
        db.add(binding)
    else:
        logger.info(f"更新现有绑定: user_id={user_id}, template={template_name}")
        binding.updated_at = datetime.utcnow()
    
    db.commit()
    return True

def load_user_prompt_from_db(db, user_id):
    """从数据库加载用户提示"""
    template_name = get_bound_template_from_db(db, user_id)
    if not template_name:
        logger.warning(f"加载用户提示失败: 用户 {user_id} 没有绑定模板")
        return None
    
    template = db.query(Template).filter(Template.name == template_name).first()
    if not template:
        logger.warning(f"加载用户提示失败: 模板 {template_name} 不存在")
        return None
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.warning(f"加载用户提示失败: 用户 {user_id} 不存在")
        return template.content
    
    industry_name = "未知行业"
    if template.industry_id:
        industry = db.query(Industry).filter(Industry.id == template.industry_id).first()
        if industry:
            industry_name = industry.name
    
    from config import ENABLE_PERSONALIZED_PROMPT, PERSONALIZED_PROMPT_TEMPLATE
    if ENABLE_PERSONALIZED_PROMPT:
        try:
            personalized_template = PERSONALIZED_PROMPT_TEMPLATE
            
            if not personalized_template:
                personalized_template = """你是专业的{行业}顾问，请结合用户信息和商品信息为客户提供个性化服务。

【用户信息】
姓名：{name}
兴趣偏好：{兴趣}
最近购买：{最近购买}

【商品信息】
库存详情：{product_inventory}

当前对话内容：{user_input}
请基于以上信息进行自然回复。"""
            
            from config import USER_PROFILE_PLACEHOLDER_PREFIX, USER_PROFILE_PLACEHOLDER_SUFFIX
            prefix = USER_PROFILE_PLACEHOLDER_PREFIX
            suffix = USER_PROFILE_PLACEHOLDER_SUFFIX
            
            from config import fill_placeholders
            
            params = {
                "行业": industry_name,
                "name": user.username or "客户",
                "兴趣": user.hobbies or "未知爱好",
                "user_input": ""
            }
            
            recent_purchases = "暂无购买记录"
            if user.profile_data:
                try:
                    import json
                    profile = json.loads(user.profile_data)
                    if "preferences" in profile and "recent_purchases" in profile["preferences"]:
                        purchases = profile["preferences"]["recent_purchases"]
                        if isinstance(purchases, list) and purchases:
                            recent_purchases = "、".join(purchases)
                except Exception as e:
                    logger.error(f"解析用户资料JSON数据失败: {str(e)}")
            params["最近购买"] = recent_purchases
            
            try:
                from inventory_processor import get_user_inventory_from_db
                inventory_data = get_user_inventory_from_db(db, user_id)
                inventory_summary = "暂无库存数据"
                if inventory_data:
                    inventory_summary = inventory_data.get("summary", "暂无库存数据")
                params["product_inventory"] = inventory_summary
            except Exception as e:
                logger.error(f"获取用户库存数据失败: {str(e)}")
                params["product_inventory"] = "暂无库存数据"
            
            personalized_template = fill_placeholders(personalized_template, params)
            
            logger.info(f"加载用户 {user_id} 的个性化提示词: 模板={template_name}, 行业={industry_name}")
            return personalized_template
        except Exception as e:
            logger.error(f"生成个性化提示词失败: {str(e)}")
            return template.content
    
    logger.info(f"加载用户 {user_id} 的提示词: 模板={template_name}")
    return template.content

def record_billing(db, user_id, tokens_used=0, duration_seconds=0.0, template_name=None):
    """记录计费信息"""
    if not user_id:
        logger.error("记录计费失败: user_id为空")
        return False
        
    user_id = user_id.strip() if isinstance(user_id, str) else user_id
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.warning(f"记录计费失败: 用户不存在 (user_id={user_id})")
        return False
    
    token_cost = (tokens_used / 1000) * 0.01
    time_cost = (duration_seconds / 60) * 0.1
    total_cost = token_cost + time_cost
    
    billing_record = BillingRecord(
        user_id=user.id,
        username=user.username,
        tokens_used=tokens_used,
        duration_seconds=duration_seconds,
        cost=total_cost,
        template_name=template_name
    )
    
    db.add(billing_record)
    db.commit()
    logger.info(f"记录计费: user_id={user_id}, tokens={tokens_used}, duration={duration_seconds:.2f}s, cost={total_cost:.4f}")
    return True

def record_ai_feeding(db, user_id, content, feedback=None):
    """记录AI投喂信息"""
    if not user_id:
        logger.error("记录AI投喂失败: user_id为空")
        return False
        
    user_id = user_id.strip() if isinstance(user_id, str) else user_id
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.warning(f"记录AI投喂失败: 用户不存在 (user_id={user_id})")
        return False
    
    feeding_record = AIFeedingRecord(
        user_id=user.id,
        content=content,
        feedback=feedback
    )
    
    db.add(feeding_record)
    db.commit()
    logger.info(f"记录AI投喂: user_id={user_id}, content_length={len(content)}")
    return True

def save_chat_message(db, context_id, user_id, role, content):
    """保存单条聊天消息"""
    from config import ENABLE_JSON_STORAGE, CHAT_STORAGE_DIR
    
    tokens_used = len(content) // 4  # 简单估算token数量
    
    message = ChatMessage(
        context_id=context_id,
        user_id=user_id,
        role=role,
        content=content,
        tokens_used=tokens_used
    )
    
    db.add(message)
    db.commit()
    
    if ENABLE_JSON_STORAGE:
        try:
            from chat_storage import ChatStorage
            
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                chat_storage = ChatStorage(CHAT_STORAGE_DIR)
                
                message_data = {
                    'role': role,
                    'content': content,
                    'time': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'tokens': tokens_used
                }
                
                user_id_clean = user.user_id.strip() if user.user_id else "unknown"
                chat_storage.save_message(user_id_clean, context_id, message_data)
                logger.info(f"消息已保存到JSON: user_id={user_id_clean}, context_id={context_id}, role={role}")
        except Exception as e:
            logger.error(f"保存消息到JSON失败: {str(e)}")
    
    return message

def get_chat_messages(db, context_id):
    """获取指定上下文的所有聊天消息"""
    from config import ENABLE_JSON_STORAGE, CHAT_STORAGE_DIR, SYNC_DB_WITH_JSON
    
    db_messages = db.query(ChatMessage).filter(
        ChatMessage.context_id == context_id
    ).order_by(ChatMessage.created_at).all()
    
    if ENABLE_JSON_STORAGE and SYNC_DB_WITH_JSON:
        try:
            context = db.query(Context).filter(Context.id == context_id).first()
            if context:
                user = db.query(User).filter(User.id == context.user_id).first()
                if user:
                    from chat_storage import ChatStorage
                    chat_storage = ChatStorage(CHAT_STORAGE_DIR)
                    
                    user_id_clean = user.user_id.strip() if user.user_id else "unknown"
                    json_messages = chat_storage.get_messages(user_id_clean, context_id)
                    
                    if json_messages and not db_messages:
                        for msg in json_messages:
                            save_chat_message(
                                db, 
                                context_id, 
                                user.id, 
                                msg.get('role', 'system'), 
                                msg.get('content', '')
                            )
                        
                        db_messages = db.query(ChatMessage).filter(
                            ChatMessage.context_id == context_id
                        ).order_by(ChatMessage.created_at).all()
                        
                        logger.info(f"从JSON同步了 {len(json_messages)} 条消息到数据库: context_id={context_id}")
        except Exception as e:
            logger.error(f"从JSON获取消息失败: {str(e)}")
    
    return db_messages

def get_chat_messages_from_json(db, context_id, max_messages=None):
    """从JSON文件获取聊天消息
    
    Args:
        db: 数据库会话
        context_id: 上下文ID
        max_messages: 最大消息数量，如果为None则返回所有消息
        
    Returns:
        消息列表，每个消息包含role, content, time, tokens字段
    """
    from config import CHAT_STORAGE_DIR, ENABLE_JSON_STORAGE
    
    if not ENABLE_JSON_STORAGE:
        return []
    
    try:
        context = db.query(Context).filter(Context.id == context_id).first()
        if not context:
            logger.warning(f"获取JSON消息失败: 上下文不存在 (context_id={context_id})")
            return []
        
        user = db.query(User).filter(User.id == context.user_id).first()
        if not user:
            logger.warning(f"获取JSON消息失败: 用户不存在 (user_id={context.user_id})")
            return []
        
        from chat_storage import ChatStorage
        chat_storage = ChatStorage(CHAT_STORAGE_DIR)
        
        user_id_clean = user.user_id.strip() if user.user_id else "unknown"
        messages = chat_storage.get_context_messages(user_id_clean, context_id, max_messages)
        
        logger.info(f"从JSON获取了 {len(messages)} 条消息: user_id={user_id_clean}, context_id={context_id}")
        return messages
    except Exception as e:
        logger.error(f"从JSON获取消息失败: {str(e)}")
        return []

class TokenPackage(Base):
    __tablename__ = "token_packages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    description = Column(Text, nullable=True)
    token_amount = Column(Integer, default=0)
    price = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    context_id = Column(Integer, ForeignKey("contexts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20))  # 'user' 或 'assistant'
    content = Column(Text)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    context = relationship("Context", back_populates="messages")
    user = relationship("User")

class InventoryUpload(Base):
    __tablename__ = 'inventory_uploads'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    filename = Column(String(255))
    original_filename = Column(String(255), nullable=True)
    file_path = Column(String(255))
    type = Column(String(50), default='inventory')  # 'inventory' 或 'product'
    status = Column(String(20), default='processing')  # 'processing', 'success', 'failed'
    notes = Column(Text, nullable=True)
    upload_time = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="inventory_uploads")
    inventory_items = relationship("InventoryItem", back_populates="inventory_upload", cascade="all, delete-orphan")

class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    
    id = Column(Integer, primary_key=True)
    inventory_upload_id = Column(Integer, ForeignKey('inventory_uploads.id'))
    product_name = Column(String(255))
    product_id = Column(String(100), nullable=True)
    quantity = Column(Integer, default=0)
    price = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    inventory_upload = relationship("InventoryUpload", back_populates="inventory_items")
    images = relationship("ProductImage", back_populates="inventory_item")

class TokenPackagePurchase(Base):
    __tablename__ = "token_package_purchases"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    package_id = Column(Integer, ForeignKey("token_packages.id"))
    purchase_time = Column(DateTime, default=datetime.utcnow)
    token_amount = Column(Integer, default=0)
    price = Column(Float, default=0.0)
    status = Column(String(20), default='pending')  # 'pending', 'success', 'failed'
    payment_method = Column(String(50), nullable=True)
    transaction_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="package_purchases")
    package = relationship("TokenPackage")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_number = Column(String(50), unique=True, index=True)
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default='pending')  # 'pending', 'processing', 'completed', 'cancelled'
    payment_status = Column(String(20), default='unpaid')  # 'unpaid', 'paid', 'refunded'
    payment_method = Column(String(50), nullable=True)
    shipping_address = Column(Text, nullable=True)
    contact_info = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_name = Column(String(255))
    product_id = Column(String(100), nullable=True)
    quantity = Column(Integer, default=1)
    price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("Order", back_populates="items")

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    product_name = Column(String(255))
    product_id = Column(String(100), nullable=True)
    quantity = Column(Integer, default=1)
    price = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    sale_date = Column(DateTime, default=datetime.utcnow)
    payment_method = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="sales")
    order = relationship("Order", back_populates="sales")

User.inventory_uploads = relationship("InventoryUpload", back_populates="user")
User.orders = relationship("Order", back_populates="user")
User.sales = relationship("Sale", back_populates="user")

Order.sales = relationship("Sale", back_populates="order")

class WechatContact(Base):
    __tablename__ = "wechat_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    wechat_id = Column(String(100), index=True, nullable=False)  # 微信ID
    nickname = Column(String(100), nullable=True)  # 昵称
    remark = Column(String(100), nullable=True)  # 备注
    is_group = Column(Boolean, default=False)  # 是否为群
    avatar = Column(Text, nullable=True)  # 头像数据，Base64编码或链接
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 关联的微信账号ID
    parent_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=True)  # 关联的微信账号ID
    ai_reply_enabled = Column(Boolean, default=True)  # 是否启用AI自动回复
    keyword_filter_enabled = Column(Boolean, default=False)  # 是否启用关键词过滤
    ai_strategy_id = Column(Integer, ForeignKey("ai_strategies.id"), nullable=True)  # AI回复策略
    last_sync_time = Column(DateTime, default=datetime.utcnow)  # 最后同步时间
    last_active_at = Column(DateTime, default=datetime.utcnow)  # 最后活动时间
    unread_count = Column(Integer, default=0)  # 未读消息数量
    
    auto_follow_enabled = Column(Boolean, default=False)  # 是否启用自动跟踪
    follow_frequency = Column(String(20), default='daily')  # 跟踪频率：daily, weekly, monthly
    last_follow_time = Column(DateTime, nullable=True)  # 最后跟踪时间
    follow_template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)  # 跟踪话术模板
    customer_type = Column(String(20), default='潜在客户')  # 客户类型：成交客户、高意向客户、潜在客户
    follow_disabled_by_user = Column(Boolean, default=False)  # 用户申请减少打扰
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # 添加自引用关系
    parent = relationship("WechatContact", remote_side=[id], backref="contacts")
    owner = relationship("User", back_populates="contacts")
    ai_strategy = relationship("AIStrategy", back_populates="contacts")
    messages = relationship("WechatMessage", back_populates="contact")

class WechatMessage(Base):
    __tablename__ = "wechat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=False)
    sender_id = Column(String(100), nullable=False)  # 发送者微信ID
    content = Column(Text, nullable=False)  # 消息内容
    content_type = Column(String(20), default="text")  # 消息类型：text, image
    image_url = Column(String(255), nullable=True)  # 图片URL（如果是图片消息）
    is_from_ai = Column(Boolean, default=False)  # 是否由AI发送
    is_read = Column(Boolean, default=False)  # 是否已读
    scheduled_time = Column(DateTime, nullable=True)  # 定时发送时间
    status = Column(String(20), default="sent")  # 状态：sent, pending, failed
    message_id = Column(String(255), unique=True, nullable=True)
    ack_status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    contact = relationship("WechatContact", back_populates="messages")

class AIStrategy(Base):
    __tablename__ = "ai_strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 策略名称
    description = Column(Text, nullable=True)  # 策略描述
    prompt_template = Column(Text, nullable=False)  # 提示词模板
    system_message = Column(Text, nullable=True)  # 系统消息
    temperature = Column(Float, default=0.7)  # 温度参数
    max_tokens = Column(Integer, default=2000)  # 最大token数
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    contacts = relationship("WechatContact", back_populates="ai_strategy")

class KeywordFilter(Base):
    __tablename__ = "keyword_filters"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=False)
    keyword = Column(String(100), nullable=False)  # 关键词
    response = Column(Text, nullable=True)  # 自定义回复内容
    is_regex = Column(Boolean, default=False)  # 是否为正则表达式
    created_at = Column(DateTime, default=datetime.utcnow)
    
    contact = relationship("WechatContact")

User.contacts = relationship("WechatContact", back_populates="owner")

class Moment(Base):
    __tablename__ = "moments"
    
    id = Column(Integer, primary_key=True, index=True)
    wechat_id = Column(String(100), index=True, nullable=False)
    content = Column(Text, nullable=True)
    media_urls = Column(Text, nullable=True)  # 存储JSON字符串，兼容旧版MySQL
    created_time = Column(DateTime, default=datetime.utcnow)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="moments")
    comments = relationship("MomentComment", back_populates="moment", cascade="all, delete-orphan")

class MomentComment(Base):
    __tablename__ = "moment_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    moment_id = Column(Integer, ForeignKey("moments.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("moment_comments.id"), nullable=True)
    wechat_id = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    created_time = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    moment = relationship("Moment", back_populates="comments")
    parent = relationship("MomentComment", remote_side=[id], backref="replies")

User.moments = relationship("Moment", back_populates="owner")

class IntentTracking(Base):
    """意向分层跟踪表"""
    __tablename__ = "intent_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=True)
    intent_type = Column(String(50), nullable=False)  # 高意向、一般意向、沉默、已成交
    intent_change = Column(String(20), nullable=True)  # 上升、下降、成交、流失
    confidence_score = Column(Float, default=0.0)  # 置信度 0-1
    detected_at = Column(DateTime, default=datetime.utcnow)
    context_data = Column(Text, nullable=True)  # JSON格式存储上下文
    source = Column(String(20), default='AI')  # 来源：AI/人工
    notes = Column(Text, nullable=True)  # 备注说明
    
    user = relationship("User")
    contact = relationship("WechatContact")


class CustomerProfile(Base):
    """客户画像详细信息表"""
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=False)
    profile_type = Column(String(50), nullable=False)  # 画像类型：兴趣、行为、偏好等
    profile_value = Column(Text, nullable=False)  # 画像值
    confidence = Column(Float, default=0.0)  # 置信度
    source = Column(String(20), default='AI')  # 来源：AI/人工
    value_level = Column(String(50), default="潜在用户")  # ★ 新增
    activity_score = Column(Float, default=0.0)  # ★ 新增
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contact = relationship("WechatContact")


class HumanAgent(Base):
    """人工客服配置表"""
    __tablename__ = "human_agents"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 所属用户
    agent_wechat_id = Column(String(100), nullable=False)  # 人工客服微信ID
    agent_name = Column(String(100), nullable=True)  # 客服姓名
    is_default = Column(Boolean, default=False)  # 是否为默认客服
    priority = Column(Integer, default=1)  # 优先级，数字越小优先级越高
    is_active = Column(Boolean, default=True)  # 是否激活
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User")

class ProactiveMessage(Base):
    """主动消息记录表"""
    __tablename__ = "proactive_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=False)
    message_type = Column(String(50), nullable=False)  # 消息类型：关怀、营销、复购提醒等
    content = Column(Text, nullable=False)  # 消息内容
    scheduled_time = Column(DateTime, nullable=True)  # 计划发送时间
    sent_time = Column(DateTime, nullable=True)  # 实际发送时间
    status = Column(String(20), default='pending')  # 状态：pending, sent, failed
    response_received = Column(Boolean, default=False)  # 是否收到回复
    created_at = Column(DateTime, default=datetime.utcnow)
    
    contact = relationship("WechatContact")

class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operation_type = Column(String(50), nullable=False)  # 操作类型
    operation_desc = Column(Text, nullable=False)  # 操作描述
    target_type = Column(String(50), nullable=True)  # 目标类型
    target_id = Column(String(50), nullable=True)  # 目标ID
    ip_address = Column(String(50), nullable=True)  # IP地址
    user_agent = Column(Text, nullable=True)  # 用户代理
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")

class ProductImage(Base):
    __tablename__ = 'product_images'
    
    id = Column(Integer, primary_key=True)
    inventory_item_id = Column(Integer, ForeignKey('inventory_items.id'))
    image_path = Column(String(500))
    original_filename = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    inventory_item = relationship("InventoryItem", back_populates="images")

if __name__ == "__main__":
    create_tables()
