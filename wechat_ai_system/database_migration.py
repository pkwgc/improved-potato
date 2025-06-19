import logging
from sqlalchemy import text
from database import get_db, engine

logger = logging.getLogger(__name__)

def detect_database_type():
    """检测数据库类型"""
    try:
        db_url = str(engine.url)
        if 'mysql' in db_url or 'pymysql' in db_url:
            return 'mysql'
        elif 'sqlite' in db_url:
            return 'sqlite'
        else:
            return 'unknown'
    except:
        return 'sqlite'  # 默认使用sqlite

def get_auto_increment_syntax(db_type):
    """根据数据库类型返回自增语法"""
    if db_type == 'mysql':
        return 'AUTO_INCREMENT'
    else:
        return 'AUTOINCREMENT'

def get_boolean_syntax(db_type):
    """根据数据库类型返回布尔值语法"""
    if db_type == 'mysql':
        return 'TINYINT(1)'
    else:
        return 'BOOLEAN'

def migrate_database():
    """执行数据库迁移，添加新字段和表"""
    db = next(get_db())
    db_type = detect_database_type()
    auto_increment = get_auto_increment_syntax(db_type)
    boolean_type = get_boolean_syntax(db_type)
    
    logger.info(f"检测到数据库类型: {db_type}")
    
    try:
        user_fields = [
            ("tags", "TEXT"),
            ("value_level", "VARCHAR(20) DEFAULT '普通'"),
            ("activity_score", "FLOAT DEFAULT 0.0"),
            ("last_active_time", "DATETIME"),
            ("order_amount_total", "FLOAT DEFAULT 0.0"),
            ("conversion_rate", "FLOAT DEFAULT 0.0"),
            ("profile_desc", "TEXT"),
            ("tag_source", "VARCHAR(20) DEFAULT 'AI'"),
            ("max_wechat_accounts", "INTEGER DEFAULT 1"),
            ("real_name", "VARCHAR(100) DEFAULT ''"),
            ("id_number", "VARCHAR(20) DEFAULT ''"),
            ("phone", "VARCHAR(20) DEFAULT ''"),
            ("email", "VARCHAR(100) DEFAULT ''")
        ]
        
        for field_name, field_type in user_fields:
            try:
                db.execute(text(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"))
                logger.info(f"已添加users表字段: {field_name}")
            except Exception as e:
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    logger.info(f"字段 {field_name} 已存在，跳过")
                else:
                    logger.error(f"添加字段 {field_name} 失败: {str(e)}")
        
        contact_fields = [
            ("auto_follow_enabled", f"{boolean_type} DEFAULT 0"),
            ("follow_frequency", "VARCHAR(20) DEFAULT 'daily'"),
            ("last_follow_time", "DATETIME"),
            ("follow_template_id", "INTEGER"),
            ("customer_type", "VARCHAR(20) DEFAULT '潜在客户'"),
            ("follow_disabled_by_user", f"{boolean_type} DEFAULT 0")
        ]
        
        for field_name, field_type in contact_fields:
            try:
                db.execute(text(f"ALTER TABLE wechat_contacts ADD COLUMN {field_name} {field_type}"))
                logger.info(f"已添加wechat_contacts表字段: {field_name}")
            except Exception as e:
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    logger.info(f"字段 {field_name} 已存在，跳过")
                else:
                    logger.error(f"添加字段 {field_name} 失败: {str(e)}")
        
        if db_type == 'mysql':
            new_tables = [
                f"""
                CREATE TABLE IF NOT EXISTS intent_tracking (
                    id INT PRIMARY KEY {auto_increment},
                    user_id INT NOT NULL,
                    contact_id INT,
                    intent_type VARCHAR(50) NOT NULL,
                    intent_change VARCHAR(20),
                    confidence_score DECIMAL(3,2) DEFAULT 0.0,
                    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    context_data TEXT,
                    source VARCHAR(20) DEFAULT 'AI',
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (contact_id) REFERENCES wechat_contacts(id)
                )
                """,
                f"""
                CREATE TABLE IF NOT EXISTS customer_profiles (
                    id INT PRIMARY KEY {auto_increment},
                    contact_id INT NOT NULL,
                    profile_type VARCHAR(50) NOT NULL,
                    profile_value TEXT NOT NULL,
                    confidence DECIMAL(3,2) DEFAULT 0.0,
                    source VARCHAR(20) DEFAULT 'AI',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_id) REFERENCES wechat_contacts(id)
                )
                """,
                f"""
                CREATE TABLE IF NOT EXISTS human_agents (
                    id INT PRIMARY KEY {auto_increment},
                    owner_id INT NOT NULL,
                    agent_wechat_id VARCHAR(100) NOT NULL,
                    agent_name VARCHAR(100),
                    is_default {boolean_type} DEFAULT 0,
                    priority INT DEFAULT 1,
                    is_active {boolean_type} DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                )
                """,
                f"""
                CREATE TABLE IF NOT EXISTS proactive_messages (
                    id INT PRIMARY KEY {auto_increment},
                    contact_id INT NOT NULL,
                    message_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    scheduled_time DATETIME,
                    sent_time DATETIME,
                    status VARCHAR(20) DEFAULT 'pending',
                    response_received {boolean_type} DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_id) REFERENCES wechat_contacts(id)
                )
                """,
                f"""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INT PRIMARY KEY {auto_increment},
                    user_id INT,
                    operation_type VARCHAR(50) NOT NULL,
                    operation_desc TEXT NOT NULL,
                    target_type VARCHAR(50),
                    target_id VARCHAR(50),
                    ip_address VARCHAR(50),
                    user_agent TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            ]
        else:
            new_tables = [
                f"""
                CREATE TABLE IF NOT EXISTS intent_tracking (
                    id INTEGER PRIMARY KEY {auto_increment},
                    user_id INTEGER NOT NULL,
                    contact_id INTEGER,
                    intent_type VARCHAR(50) NOT NULL,
                    intent_change VARCHAR(20),
                    confidence_score REAL DEFAULT 0.0,
                    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    context_data TEXT,
                    source VARCHAR(20) DEFAULT 'AI',
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (contact_id) REFERENCES wechat_contacts(id)
                )
                """,
                f"""
                CREATE TABLE IF NOT EXISTS customer_profiles (
                    id INTEGER PRIMARY KEY {auto_increment},
                    contact_id INTEGER NOT NULL,
                    profile_type VARCHAR(50) NOT NULL,
                    profile_value TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    source VARCHAR(20) DEFAULT 'AI',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_id) REFERENCES wechat_contacts(id)
                )
                """,
                f"""
                CREATE TABLE IF NOT EXISTS human_agents (
                    id INTEGER PRIMARY KEY {auto_increment},
                    owner_id INTEGER NOT NULL,
                    agent_wechat_id VARCHAR(100) NOT NULL,
                    agent_name VARCHAR(100),
                    is_default INTEGER DEFAULT 0,
                    priority INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                )
                """,
                f"""
                CREATE TABLE IF NOT EXISTS proactive_messages (
                    id INTEGER PRIMARY KEY {auto_increment},
                    contact_id INTEGER NOT NULL,
                    message_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    scheduled_time DATETIME,
                    sent_time DATETIME,
                    status VARCHAR(20) DEFAULT 'pending',
                    response_received INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_id) REFERENCES wechat_contacts(id)
                )
                """,
                f"""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY {auto_increment},
                    user_id INTEGER,
                    operation_type VARCHAR(50) NOT NULL,
                    operation_desc TEXT NOT NULL,
                    target_type VARCHAR(50),
                    target_id VARCHAR(50),
                    ip_address VARCHAR(50),
                    user_agent TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            ]
        
        for i, table_sql in enumerate(new_tables):
            try:
                db.execute(text(table_sql))
                table_names = ['intent_tracking', 'customer_profiles', 'human_agents', 'proactive_messages', 'operation_logs']
                logger.info(f"已创建新表: {table_names[i]}")
            except Exception as e:
                if "already exists" in str(e) or "Table" in str(e) and "already exists" in str(e):
                    logger.info(f"表 {table_names[i]} 已存在，跳过")
                else:
                    logger.error(f"创建表失败: {str(e)}")
        
        db.commit()
        logger.info("数据库迁移完成")
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_database()
