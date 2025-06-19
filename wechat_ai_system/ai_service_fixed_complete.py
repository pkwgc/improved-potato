import json
import re
import time
import logging
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from database import User, Template, Context, BillingRecord, Industry, save_context_to_db, record_billing, save_chat_message
from intent_recognition import recognize_intent

logger = logging.getLogger(__name__)

TEMPLATE_CACHE: Dict[str, Dict[str, Any]] = {}

class AIService:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", 
                 model: str = "deepseek-chat", max_tokens: int = 1024, 
                 temperature: float = 0.7):
        """初始化AI服务
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            max_tokens: 最大生成token数量
            temperature: 温度参数
        """
        import httpx
        http_client = httpx.Client()
        self.client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        logger.info(f"AIService初始化成功: model={model}, max_tokens={max_tokens}, temperature={temperature}")

    def process_chat(self, db: Session, user_id: str, user_message: str, 
                     template_name: str, username: Optional[str] = None,
                     prompt_override: Optional[str] = None) -> Dict[str, Any]:
        """处理聊天请求
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            user_message: 用户消息
            template_name: 模板名称
            username: 用户名称
            prompt_override: 覆盖提示词
            
        Returns:
            处理结果字典
        """
        start_time = time.time()
        logger.info(f"处理聊天请求: user_id={user_id}, template={template_name}, message={user_message[:30]}...")

        industry_name = self._get_industry_name(db, template_name)
        intent_result = recognize_intent(db, user_message, industry_name)
        if intent_result["trigger_api"]:
            return self._handle_intent_reply(db, user_id, user_message, intent_result)

        chat_contexts = self._load_context(db, user_id, template_name)
        chat_contexts.append({"role": "user", "content": str(user_message)})
        chat_contexts = self._clean_context(chat_contexts)

        user_prompt = prompt_override or self._get_template_with_cache(db, template_name, user_id)
        logger.info(f"使用提示词: {user_prompt[:100]}...")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": user_prompt}] + chat_contexts,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False
            )
            result = response.model_dump()
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                reply, confidence = self.extract_reply_and_confidence(content)

                context = save_context_to_db(db, user_id, template_name, chat_contexts + [{"role": "assistant", "content": reply}], username)
                user_obj = db.query(User).filter(User.user_id == user_id).first()
                if user_obj and context:
                    save_chat_message(db, context.id, user_obj.id, "user", user_message)
                    save_chat_message(db, context.id, user_obj.id, "assistant", reply)

                tokens_used = result.get("usage", {}).get("total_tokens", 0)
                if user_obj:
                    user_obj.token_balance = max(0, user_obj.token_balance - tokens_used)
                    db.commit()
                record_billing(db, user_id, tokens_used, time.time() - start_time, template_name)
                logger.info(f"AI回复成功: user_id={user_id}, tokens={tokens_used}, time={time.time() - start_time:.2f}s")
                return {"reply": reply, "confidence": confidence, "trigger_api": False, "raw_content": content}

            logger.error(f"API响应无效: {result}")
            return {"error": "API response invalid", "trigger_api": False}

        except Exception as e:
            logger.error(f"DeepSeek API 调用出错：{str(e)}")
            return {"error": f"AI服务错误: {str(e)}", "trigger_api": False}

    def _get_template_with_cache(self, db: Session, template_name: str, user_id: Optional[str] = None) -> str:
        """获取模板内容，使用缓存提高性能"""
        template = db.query(Template).filter(Template.name == template_name).first()
        if not template:
            logger.error(f"[模板错误] 模板未找到：{template_name}，请在后台管理界面创建该模板")
            return f"错误：模板 '{template_name}' 未找到，请联系管理员在后台创建该模板。"

        cache = TEMPLATE_CACHE.get(template_name)
        if cache and cache["updated_at"] == str(template.updated_at):
            template_content = cache["content"]
        else:
            template_content = template.content
            TEMPLATE_CACHE[template_name] = {
                "content": template_content,
                "updated_at": str(template.updated_at)
            }
            logger.warning(f"[缓存刷新] 模板：{template_name} 内容已更新，重新缓存")
        
        from config import ENABLE_USER_PROFILE, USER_PROFILE_PLACEHOLDER_PREFIX, USER_PROFILE_PLACEHOLDER_SUFFIX
        from config import ENABLE_PERSONALIZED_PROMPT, PERSONALIZED_PROMPT_TEMPLATE
        
        if ENABLE_USER_PROFILE and user_id:
            template_content = self._replace_user_profile_placeholders(db, template_content, user_id)
        
        if ENABLE_PERSONALIZED_PROMPT and user_id:
            try:
                user_data = self._get_user_data_for_personalized_prompt(db, user_id)
                
                industry_name = self._get_industry_name(db, template_name)
                if industry_name:
                    user_data["行业"] = industry_name
                
                from inventory_processor import process_personalized_prompt_template
                personalized_prompt = process_personalized_prompt_template(PERSONALIZED_PROMPT_TEMPLATE, user_data)
                
                template_content = personalized_prompt + "\n\n" + template_content
                logger.info(f"[添加个性化提示词] {personalized_prompt[:100]}...")
            except Exception as e:
                logger.error(f"处理个性化提示词出错: {str(e)}")
        
        return template_content
        
    def _get_user_data_for_personalized_prompt(self, db: Session, user_id: str) -> Dict[str, Any]:
        """获取用户数据用于个性化提示词"""
        user_data = {}
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"获取用户数据失败: 用户不存在 (user_id={user_id})")
            return user_data
            
        user_data["name"] = user.username or "未知用户"
        
        if hasattr(user, 'identity') and user.identity:
            user_data["行业"] = user.identity
        else:
            user_data["行业"] = ""
            
        if hasattr(user, 'hobbies') and user.hobbies:
            user_data["兴趣"] = user.hobbies
        else:
            user_data["兴趣"] = ""
        
        user_data["最近购买"] = ""
        
        if hasattr(user, 'profile_data') and user.profile_data:
            try:
                import json
                profile = json.loads(user.profile_data)
                
                if "preferences" in profile and "recent_purchases" in profile["preferences"]:
                    recent_purchases = profile["preferences"].get("recent_purchases", [])
                    if isinstance(recent_purchases, list) and recent_purchases:
                        user_data["最近购买"] = "、".join(recent_purchases)
            except Exception as e:
                logger.error(f"解析用户资料JSON数据失败: {str(e)}")
        
        try:
            from inventory_processor import get_user_inventory_from_db
            inventory_data = get_user_inventory_from_db(db, user_id)
            if inventory_data:
                user_data["product_inventory"] = inventory_data.get("summary", "")
                logger.info(f"获取到用户库存数据: {user_data['product_inventory'][:100]}...")
            else:
                user_data["product_inventory"] = ""
                logger.warning(f"用户没有库存数据: {user_id}")
        except Exception as e:
            logger.error(f"获取用户库存数据失败: {str(e)}")
            user_data["product_inventory"] = ""
            
        return user_data

    def _get_industry_name(self, db: Session, template_name: str) -> Optional[str]:
        """获取模板对应的行业名称"""
        template = db.query(Template).filter(Template.name == template_name).first()
        if template and template.industry_id:
            industry = db.query(Industry).filter(Industry.id == template.industry_id).first()
            return industry.name if industry else None
        return None

    def _handle_intent_reply(self, db, user_id, user_message, intent_result):
        """处理意图识别结果"""
        tokens_used = len(user_message) + 100
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            if user.token_balance <= 0:
                return {"intent": None, "confidence": 0, "usage": {"total_tokens": 0}}
            user.token_balance = max(0, user.token_balance - tokens_used)
            db.commit()
        record_billing(db, user_id, tokens_used=tokens_used)
        return intent_result

    def extract_reply_and_confidence(self, content: str) -> Tuple[str, float]:
        """从AI回复中提取回复内容和置信度"""
        reply = content
        confidence = 0
        try:
            match = re.search(r'{.*}', content, re.DOTALL)
            if match:
                json_str = re.sub(r'(?<!\\)\\(?![\\/"bfnrtu])', r'\\\\', match.group())
                parsed = json.loads(json_str)
                reply = parsed.get("reply", content)
                confidence = parsed.get("confidence", 0)
        except Exception as e:
            logger.warning(f"reply/confidence 提取失败：{e}")
        return reply, confidence

    def _load_context(self, db: Session, user_id: str, template_name: str) -> List[Dict[str, str]]:
        """加载用户上下文"""
        from database import load_context_from_db
        contexts = load_context_from_db(db, user_id, template_name)
        return contexts or []

    def _clean_context(self, contexts: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """清理上下文，保持在合理长度"""
        from config import MAX_CONTEXT_MESSAGES
        contexts = [msg for msg in contexts if msg["role"] in ["user", "assistant"]]
        while len(contexts) > MAX_CONTEXT_MESSAGES * 2:
            contexts.pop(0)
        return contexts
        
    def _replace_user_profile_placeholders(self, db: Session, template_content: str, user_id: str) -> str:
        """替换模板中的用户资料占位符"""
        from config import USER_PROFILE_PLACEHOLDER_PREFIX as prefix, USER_PROFILE_PLACEHOLDER_SUFFIX as suffix
        from database import User
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return template_content
        
        replacements = {
            f"{prefix}user_id{suffix}": user.user_id,
            f"{prefix}username{suffix}": user.username,
            f"{prefix}name{suffix}": user.username  # 为了兼容{name}占位符
        }
        
        if hasattr(user, 'identity') and user.identity:
            replacements[f"{prefix}identity{suffix}"] = user.identity
            replacements[f"{prefix}行业{suffix}"] = user.identity  # 为了兼容{行业}占位符
        else:
            replacements[f"{prefix}identity{suffix}"] = "未知身份"
            replacements[f"{prefix}行业{suffix}"] = "未知行业"
            
        if hasattr(user, 'hobbies') and user.hobbies:
            replacements[f"{prefix}hobbies{suffix}"] = user.hobbies
            replacements[f"{prefix}兴趣{suffix}"] = user.hobbies  # 为了兼容{兴趣}占位符
        else:
            replacements[f"{prefix}hobbies{suffix}"] = "未知爱好"
            replacements[f"{prefix}兴趣{suffix}"] = "未知爱好"
        
        replacements[f"{prefix}最近购买{suffix}"] = "暂无购买记录"
        
        try:
            from inventory_processor import get_user_inventory_from_db
            inventory_data = get_user_inventory_from_db(db, user_id)
            if inventory_data:
                replacements[f"{prefix}product_inventory{suffix}"] = inventory_data.get("summary", "暂无库存数据")
            else:
                replacements[f"{prefix}product_inventory{suffix}"] = "暂无库存数据"
        except Exception as e:
            logger.error(f"获取用户库存数据失败: {str(e)}")
            replacements[f"{prefix}product_inventory{suffix}"] = "暂无库存数据"
        
        if hasattr(user, 'profile_data') and user.profile_data:
            try:
                import json
                profile = json.loads(user.profile_data)
                
                if "contact_info" in profile:
                    contact_info = profile["contact_info"]
                    for key, value in contact_info.items():
                        replacements[f"{prefix}contact_{key}{suffix}"] = str(value)
                
                if "preferences" in profile:
                    preferences = profile["preferences"]
                    for key, value in preferences.items():
                        replacements[f"{prefix}pref_{key}{suffix}"] = str(value)
                    
                    if "recent_purchases" in preferences:
                        recent_purchases = preferences.get("recent_purchases", [])
                        if isinstance(recent_purchases, list) and recent_purchases:
                            replacements[f"{prefix}最近购买{suffix}"] = "、".join(recent_purchases)
                
                for key, value in profile.items():
                    if key not in ["contact_info", "preferences"]:
                        replacements[f"{prefix}profile_{key}{suffix}"] = str(value)
            except Exception as e:
                logger.error(f"解析用户资料JSON数据失败: {str(e)}")
        
        result = template_content
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        return result
