import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from urllib.parse import quote_plus
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)

load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True)
    username = Column(String(50), index=True)
    password = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    token_limit = Column(Integer, default=0)
    token_balance = Column(Integer, default=0)
    token_package = Column(String(50), nullable=True)
    has_appointment = Column(Boolean, default=False)
    identity = Column(String(200), nullable=True)
    hobbies = Column(String(500), nullable=True)
    profile_data = Column(Text, nullable=True)
    
    real_name = Column(String(100), default='')
    id_number = Column(String(20), default='')
    phone = Column(String(20), default='')
    email = Column(String(100), default='')
    
    tags = Column(Text, nullable=True)
    value_level = Column(String(20), default='普通')
    activity_score = Column(Float, default=0.0)
    last_active_time = Column(DateTime, nullable=True)
    order_amount_total = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    profile_desc = Column(Text, nullable=True)
    tag_source = Column(String(20), default='AI')
    
    max_wechat_accounts = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    contacts = relationship("WechatContact", back_populates="owner")

class WechatContact(Base):
    __tablename__ = "wechat_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    wechat_id = Column(String(100), index=True, nullable=False)
    nickname = Column(String(100), nullable=True)
    remark = Column(String(100), nullable=True)
    is_group = Column(Boolean, default=False)
    avatar = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=True)
    ai_reply_enabled = Column(Boolean, default=True)
    keyword_filter_enabled = Column(Boolean, default=False)
    ai_strategy_id = Column(Integer, ForeignKey("ai_strategies.id"), nullable=True)
    last_sync_time = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    unread_count = Column(Integer, default=0)
    mainnumber = Column(Boolean, default=False)
    profile_data = Column(Text, nullable=True)
    
    auto_follow_enabled = Column(Boolean, default=False)
    follow_frequency = Column(String(20), default='daily')
    last_follow_time = Column(DateTime, nullable=True)
    follow_template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    customer_type = Column(String(20), default='潜在客户')
    follow_disabled_by_user = Column(Boolean, default=False)
    tags = Column(Text, nullable=True)
    require_approval = Column(Boolean, default=True)
    tracking_start_date = Column(DateTime, nullable=True)
    current_period = Column(Integer, default=1)
    period_contact_count = Column(Integer, default=0)
    silence_period_count = Column(Integer, default=0)
    is_silenced = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    parent = relationship("WechatContact", remote_side=[id], backref="contacts")
    owner = relationship("User", back_populates="contacts")
    messages = relationship("WechatMessage", back_populates="contact")

class WechatMessage(Base):
    __tablename__ = "wechat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=False)
    sender_id = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default="text")
    image_url = Column(String(255), nullable=True)
    is_from_ai = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    scheduled_time = Column(DateTime, nullable=True)
    status = Column(String(20), default="sent")
    message_id = Column(String(255), unique=True, nullable=True)
    ack_status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    contact = relationship("WechatContact", back_populates="messages")

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    content = Column(Text)
    template_type = Column(String(20), default="chat", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AIStrategy(Base):
    __tablename__ = "ai_strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    prompt_template = Column(Text, nullable=False)
    system_message = Column(Text, nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProactiveMessage(Base):
    __tablename__ = "proactive_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("wechat_contacts.id"), nullable=False)
    message_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    scheduled_time = Column(DateTime, nullable=True)
    sent_time = Column(DateTime, nullable=True)
    status = Column(String(20), default='pending')
    response_received = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    contact = relationship("WechatContact")

def create_engine_instance():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_system.db')
    DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    print(f"使用SQLite数据库: {db_path}")
    return engine

engine = create_engine_instance()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.warning(f"无法创建数据库表: {str(e)}")

def get_db():
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.warning(f"无法连接到数据库: {str(e)}")
        
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

if __name__ == "__main__":
    create_tables()
