"""
数据库迁移脚本 - 创建聊天消息表并迁移现有消息
"""

from database import Base, engine, get_db, Context, ChatMessage, User
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_chat_message_table():
    """创建聊天消息表"""
    logger.info("创建聊天消息表...")
    Base.metadata.create_all(bind=engine, tables=[ChatMessage.__table__])
    logger.info("聊天消息表创建成功！")

def migrate_existing_messages():
    """迁移现有的消息到新表"""
    logger.info("开始迁移现有消息...")
    db = next(get_db())
    try:
        count = 0
        contexts = db.query(Context).all()
        total_contexts = len(contexts)
        logger.info(f"找到 {total_contexts} 个上下文记录")
        
        for i, context in enumerate(contexts):
            try:
                if i % 10 == 0:
                    logger.info(f"处理进度: {i}/{total_contexts} ({i/total_contexts*100:.1f}%)")
                
                user = db.query(User).filter(User.user_id == context.user_id).first()
                if not user:
                    logger.warning(f"上下文ID {context.id} 的用户ID {context.user_id} 不存在，跳过")
                    continue
                
                if not context.context_data:
                    logger.warning(f"上下文ID {context.id} 没有context_data，跳过")
                    continue
                
                try:
                    content_list = eval(context.context_data)
                    
                    for msg in content_list:
                        if msg['role'] in ['user', 'assistant']:
                            tokens_used = len(msg['content']) // 4
                            chat_message = ChatMessage(
                                context_id=context.id,
                                user_id=user.id,
                                role=msg['role'],
                                content=msg['content'],
                                tokens_used=tokens_used
                            )
                            db.add(chat_message)
                            count += 1
                except (SyntaxError, ValueError) as e:
                    logger.error(f"解析上下文ID {context.id} 的context_data失败: {str(e)}")
                    try:
                        content_list = json.loads(context.context_data)
                        for msg in content_list:
                            if msg['role'] in ['user', 'assistant']:
                                tokens_used = len(msg['content']) // 4
                                chat_message = ChatMessage(
                                    context_id=context.id,
                                    user_id=user.id,
                                    role=msg['role'],
                                    content=msg['content'],
                                    tokens_used=tokens_used
                                )
                                db.add(chat_message)
                                count += 1
                    except json.JSONDecodeError:
                        logger.error(f"JSON解析上下文ID {context.id} 的context_data失败")
                
                if count % 100 == 0:
                    db.commit()
                    logger.info(f"已迁移 {count} 条消息...")
            except Exception as e:
                logger.error(f"迁移上下文ID {context.id} 失败: {str(e)}")
        
        db.commit()
        logger.info(f"迁移完成！总共迁移了 {count} 条消息。")
    finally:
        db.close()

if __name__ == "__main__":
    create_chat_message_table()
    migrate_existing_messages()
