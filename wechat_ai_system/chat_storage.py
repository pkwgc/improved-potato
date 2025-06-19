import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ChatStorage:
    """处理聊天记录的JSON存储和检索"""
    
    def __init__(self, base_dir: str = "chat_records"):
        """初始化聊天存储
        
        Args:
            base_dir: 存储聊天记录JSON文件的基础目录
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def _get_user_dir(self, user_id: str) -> str:
        """获取用户聊天记录目录
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户聊天记录目录路径
        """
        user_id = user_id.strip() if user_id else "unknown"
        user_dir = os.path.join(self.base_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def _get_context_file(self, user_id: str, context_id: int) -> str:
        """获取上下文文件路径
        
        Args:
            user_id: 用户ID
            context_id: 上下文ID
            
        Returns:
            上下文文件路径
        """
        user_dir = self._get_user_dir(user_id)
        return os.path.join(user_dir, f"context_{context_id}.json")
    
    def save_message(self, user_id: str, context_id: int, message: Dict[str, Any]) -> bool:
        """保存单条消息到JSON文件
        
        Args:
            user_id: 用户ID
            context_id: 上下文ID
            message: 消息数据，包含role, content, time等字段
            
        Returns:
            是否保存成功
        """
        try:
            user_id = user_id.strip() if user_id else "unknown"
            file_path = self._get_context_file(user_id, context_id)
            
            messages = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        messages = data.get('messages', [])
                    except json.JSONDecodeError:
                        logger.error(f"无法解析JSON文件: {file_path}")
            
            if 'time' not in message:
                message['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            messages.append(message)
            
            data = {
                'context_id': context_id,
                'user_id': user_id,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'messages': messages
            }
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"保存消息到JSON失败: {str(e)}")
            return False
    
    def save_context(self, user_id: str, context_id: int, messages: List[Dict[str, Any]]) -> bool:
        """保存整个上下文的消息到JSON文件
        
        Args:
            user_id: 用户ID
            context_id: 上下文ID
            messages: 消息列表
            
        Returns:
            是否保存成功
        """
        try:
            user_id = user_id.strip() if user_id else "unknown"
            file_path = self._get_context_file(user_id, context_id)
            
            for message in messages:
                if 'time' not in message:
                    message['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            data = {
                'context_id': context_id,
                'user_id': user_id,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'messages': messages
            }
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"保存上下文到JSON失败: {str(e)}")
            return False
    
    def get_messages(self, user_id: str, context_id: int) -> List[Dict[str, Any]]:
        """从JSON文件获取上下文的所有消息
        
        Args:
            user_id: 用户ID
            context_id: 上下文ID
            
        Returns:
            消息列表
        """
        try:
            user_id = user_id.strip() if user_id else "unknown"
            file_path = self._get_context_file(user_id, context_id)
            
            if not os.path.exists(file_path):
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    return data.get('messages', [])
                except json.JSONDecodeError:
                    logger.error(f"无法解析JSON文件: {file_path}")
                    return []
        except Exception as e:
            logger.error(f"从JSON获取消息失败: {str(e)}")
            return []
    
    def get_context_messages(self, user_id: str, context_id: int, max_messages: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取上下文的消息，可以限制最大消息数量
        
        Args:
            user_id: 用户ID
            context_id: 上下文ID
            max_messages: 最大消息数量，如果为None则返回所有消息
            
        Returns:
            消息列表
        """
        user_id = user_id.strip() if user_id else "unknown"
        messages = self.get_messages(user_id, context_id)
        
        if max_messages is not None and len(messages) > max_messages:
            return messages[-max_messages:]
        
        return messages
    
    def get_all_contexts(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有上下文
        
        Args:
            user_id: 用户ID
            
        Returns:
            上下文列表，每个上下文包含context_id和updated_at
        """
        try:
            user_id = user_id.strip() if user_id else "unknown"
            user_dir = self._get_user_dir(user_id)
            contexts = []
            
            if not os.path.exists(user_dir):
                return []
                
            for filename in os.listdir(user_dir):
                if filename.startswith("context_") and filename.endswith(".json"):
                    file_path = os.path.join(user_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            contexts.append({
                                'context_id': data.get('context_id'),
                                'updated_at': data.get('updated_at'),
                                'message_count': len(data.get('messages', []))
                            })
                    except (json.JSONDecodeError, IOError) as e:
                        logger.error(f"读取上下文文件失败: {file_path}, 错误: {str(e)}")
            
            contexts.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            return contexts
        except Exception as e:
            logger.error(f"获取所有上下文失败: {str(e)}")
            return []
    
    def delete_context(self, user_id: str, context_id: int) -> bool:
        """删除上下文文件
        
        Args:
            user_id: 用户ID
            context_id: 上下文ID
            
        Returns:
            是否删除成功
        """
        try:
            user_id = user_id.strip() if user_id else "unknown"
            file_path = self._get_context_file(user_id, context_id)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"删除上下文失败: {str(e)}")
            return False
