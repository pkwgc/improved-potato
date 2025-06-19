import os
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from database import User, Template, Context, BillingRecord, AIFeedingRecord
from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL, MAX_TOKEN, TEMPERATURE,
    MOONSHOT_API_KEY, MOONSHOT_BASE_URL, MOONSHOT_MODEL, MOONSHOT_TEMPERATURE,
    ENABLE_IMAGE_RECOGNITION, ENABLE_EMOJI_RECOGNITION
)

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key=None, base_url=None, model=None, max_tokens=None, temperature=None):
        self.template_cache = {}
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.model = model or MODEL
        self.max_token = max_tokens or MAX_TOKEN  # Store as max_token internally for compatibility
        self.temperature = temperature or TEMPERATURE
        
        self.moonshot_api_key = MOONSHOT_API_KEY
        self.moonshot_base_url = MOONSHOT_BASE_URL
        self.moonshot_model = MOONSHOT_MODEL
        self.moonshot_temperature = MOONSHOT_TEMPERATURE
        
        self.enable_image_recognition = ENABLE_IMAGE_RECOGNITION
        self.enable_emoji_recognition = ENABLE_EMOJI_RECOGNITION
    
    def process_message(self, db: Session, user_id: str, message: str, template_name: Optional[str] = None, 
                        context_id: Optional[str] = None, image_url: Optional[str] = None) -> Dict[str, Any]:
        """处理用户消息，调用AI接口获取回复"""
        try:
            from database import load_context_from_db, save_context_to_db, get_bound_template_from_db
            
            if not template_name:
                template_name = get_bound_template_from_db(db, user_id)
                if not template_name:
                    logger.error(f"用户 {user_id} 没有绑定模板，请在后台管理界面为用户绑定模板")
                    template_name = "default"
            
            template_content = self._get_template_with_cache(db, template_name, user_id)
            
            context = load_context_from_db(db, user_id, context_id)
            
            messages = []
            
            messages.append({"role": "system", "content": template_content})
            
            for ctx_msg in context:
                messages.append(ctx_msg)
            
            if image_url and self.enable_image_recognition:
                return self._process_with_moonshot(db, user_id, message, image_url, template_content, context)
            else:
                messages.append({"role": "user", "content": message})
            
            start_time = time.time()
            response = self._call_api(messages)
            end_time = time.time()
            
            if response and "choices" in response and len(response["choices"]) > 0:
                reply = response["choices"][0]["message"]["content"]
                
                new_context = context.copy()
                new_context.append({"role": "user", "content": message})
                new_context.append({"role": "assistant", "content": reply})
                
                save_context_to_db(db, user_id, new_context, context_id)
                
                from database import record_billing
                tokens_used = response.get("usage", {}).get("total_tokens", 0)
                time_used = end_time - start_time
                record_billing(db, user_id, tokens_used, time_used)
                
                return {
                    "reply": reply,
                    "tokens_used": tokens_used,
                    "time_used": round(time_used, 2)
                }
            else:
                logger.error(f"API响应格式错误: {response}")
                return {"reply": "抱歉，我遇到了一些问题，请稍后再试。", "error": "API响应格式错误"}
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            return {"reply": "抱歉，我遇到了一些问题，请稍后再试。", "error": str(e)}
    
    def _get_template_with_cache(self, db: Session, template_name: str, user_id: Optional[str] = None) -> str:
        """获取模板内容，使用缓存提高性能"""
        if template_name in self.template_cache:
            return self.template_cache[template_name]
        
        template = db.query(Template).filter(Template.name == template_name).first()
        if not template:
            logger.error(f"[模板错误] 模板未找到：{template_name}，请在后台管理界面创建该模板")
            template_content = f"错误：模板 '{template_name}' 未找到，请联系管理员在后台创建该模板。"
        else:
            template_content = template.content
        
        self.template_cache[template_name] = template_content
        
        from config import ENABLE_USER_PROFILE, USER_PROFILE_PLACEHOLDER_PREFIX, USER_PROFILE_PLACEHOLDER_SUFFIX
        from config import ENABLE_PERSONALIZED_PROMPT, PERSONALIZED_PROMPT_TEMPLATE
        
        logger.info(f"ENABLE_PERSONALIZED_PROMPT = {ENABLE_PERSONALIZED_PROMPT}")
        
        if ENABLE_USER_PROFILE and user_id:
            template_content = self._replace_user_profile_placeholders(db, template_content, user_id)
        
        if ENABLE_PERSONALIZED_PROMPT and user_id:
            try:
                logger.info(f"开始处理个性化提示词，用户ID: {user_id}")
                
                user_data = self._get_user_data_for_personalized_prompt(db, user_id)
                logger.info(f"获取到的用户数据: {user_data}")
                
                industry_name = self._get_industry_name(db, template_name)
                if industry_name:
                    user_data["行业"] = industry_name
                    logger.info(f"设置行业为: {industry_name}")
                
                user_data["user_input"] = "{user_input}"
                
                try:
                    from inventory_processor import process_personalized_prompt_template, get_user_inventory_from_db
                    logger.info(f"成功导入inventory_processor模块")
                    
                    inventory_data = get_user_inventory_from_db(db, user_id)
                    logger.info(f"获取到的库存数据: {inventory_data}")
                    
                    if inventory_data:
                        user_data["product_inventory"] = inventory_data.get("summary", "")
                        logger.info(f"设置product_inventory为: {user_data['product_inventory']}")
                    else:
                        user_data["product_inventory"] = ""
                        logger.info(f"未找到库存数据，设置product_inventory为空")
                    
                    personalized_prompt = process_personalized_prompt_template(PERSONALIZED_PROMPT_TEMPLATE, user_data)
                    logger.info(f"处理后的个性化提示词: {personalized_prompt}")
                    
                    final_template = personalized_prompt.replace("{user_input}", "")
                    template_content = final_template + "\n\n" + template_content
                    logger.info(f"最终模板内容: {template_content[:100]}...")
                except ImportError as e:
                    logger.error(f"导入inventory_processor模块失败: {str(e)}")
                    logger.error(f"无法处理个性化提示词，使用原始模板")
            except Exception as e:
                logger.error(f"处理个性化提示词出错: {str(e)}")
                logger.error(f"错误详情: {e.__class__.__name__}: {str(e)}")
                import traceback
                logger.error(f"错误堆栈: {traceback.format_exc()}")
        
        return template_content
        
    def _get_user_data_for_personalized_prompt(self, db: Session, user_id: str) -> Dict[str, Any]:
        """获取用户数据用于个性化提示词"""
        user_data = {}
        
        logger.info(f"开始获取用户数据，用户ID: {user_id}")
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.info(f"用户不存在: {user_id}")
            return user_data
            
        user_data["name"] = user.username or "未知用户"
        logger.info(f"用户名: {user_data['name']}")
        
        if hasattr(user, 'identity') and user.identity:
            user_data["行业"] = user.identity
            logger.info(f"用户行业: {user_data['行业']}")
        else:
            user_data["行业"] = ""
            logger.info(f"用户行业为空")
            
        if hasattr(user, 'hobbies') and user.hobbies:
            user_data["兴趣"] = user.hobbies
            logger.info(f"用户兴趣: {user_data['兴趣']}")
        else:
            user_data["兴趣"] = ""
            logger.info(f"用户兴趣为空")
        
        user_data["最近购买"] = ""
        
        if hasattr(user, 'profile_data') and user.profile_data:
            try:
                import json
                profile = json.loads(user.profile_data)
                logger.info(f"用户资料数据: {profile}")
                
                if "preferences" in profile and "recent_purchases" in profile["preferences"]:
                    recent_purchases = profile["preferences"].get("recent_purchases", [])
                    if isinstance(recent_purchases, list) and recent_purchases:
                        user_data["最近购买"] = "、".join(recent_purchases)
                        logger.info(f"用户最近购买: {user_data['最近购买']}")
            except Exception as e:
                logger.error(f"解析用户资料JSON数据失败: {str(e)}")
        
        logger.info(f"开始获取用户ID={user_id}的库存数据")
        try:
            from inventory_processor import get_user_inventory_from_db
            inventory_data = get_user_inventory_from_db(db, user_id)
            logger.info(f"获取到的库存数据: {inventory_data}")
            
            if inventory_data:
                user_data["product_inventory"] = inventory_data.get("summary", "")
                logger.info(f"处理后的product_inventory值: {user_data['product_inventory']}")
            else:
                user_data["product_inventory"] = ""
                logger.info(f"未找到库存数据，设置product_inventory为空")
        except Exception as e:
            logger.error(f"获取用户库存数据失败: {str(e)}")
            logger.error(f"错误详情: {e.__class__.__name__}: {str(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            user_data["product_inventory"] = ""
            
        logger.info(f"最终用户数据: {user_data}")
        return user_data

    def _get_industry_name(self, db: Session, template_name: str) -> Optional[str]:
        template = db.query(Template).filter(Template.name == template_name).first()
        if not template or not template.industry_id:
            return None
        
        from database import Industry
        industry = db.query(Industry).filter(Industry.id == template.industry_id).first()
        if not industry:
            return None
        
        return industry.name

    def _call_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用DeepSeek API"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_token  # Use max_token internally
            }
            
            response = requests.post(
                f"{self.base_url}chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API调用失败: {response.status_code} {response.text}")
                return {"error": f"API调用失败: {response.status_code}"}
        except Exception as e:
            logger.error(f"调用API时出错: {str(e)}")
            return {"error": f"调用API时出错: {str(e)}"}
    
    def _process_with_moonshot(self, db: Session, user_id: str, message: str, image_url: str, 
                              template_content: str, context: List[Dict[str, str]]) -> Dict[str, Any]:
        """使用Moonshot API处理带图片的消息"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.moonshot_api_key}"
            }
            
            messages = []
            
            messages.append({"role": "system", "content": template_content})
            
            for ctx_msg in context:
                messages.append(ctx_msg)
            
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
            
            data = {
                "model": self.moonshot_model,
                "messages": messages,
                "temperature": self.moonshot_temperature,
                "max_tokens": self.max_token  # Use max_token internally
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.moonshot_base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            end_time = time.time()
            
            if response.status_code == 200:
                response_data = response.json()
                
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    reply = response_data["choices"][0]["message"]["content"]
                    
                    new_context = context.copy()
                    new_context.append({"role": "user", "content": f"{message} [图片]"})
                    new_context.append({"role": "assistant", "content": reply})
                    
                    from database import save_context_to_db
                    save_context_to_db(db, user_id, new_context, None)
                    
                    from database import record_billing
                    tokens_used = response_data.get("usage", {}).get("total_tokens", 0)
                    time_used = end_time - start_time
                    record_billing(db, user_id, tokens_used, time_used)
                    
                    return {
                        "reply": reply,
                        "tokens_used": tokens_used,
                        "time_used": round(time_used, 2)
                    }
                else:
                    logger.error(f"Moonshot API响应格式错误: {response_data}")
                    return {"reply": "抱歉，我无法理解这张图片，请尝试其他图片或提供更多信息。", "error": "API响应格式错误"}
            else:
                logger.error(f"Moonshot API调用失败: {response.status_code} {response.text}")
                return {"reply": "抱歉，我无法处理这张图片，请稍后再试。", "error": f"API调用失败: {response.status_code}"}
        except Exception as e:
            logger.error(f"处理图片消息时出错: {str(e)}")
            return {"reply": "抱歉，处理图片时出错，请稍后再试。", "error": str(e)}
    
    def _replace_user_profile_placeholders(self, db: Session, template_content: str, user_id: str) -> str:
        """替换模板中的用户资料占位符"""
        from config import USER_PROFILE_PLACEHOLDER_PREFIX as prefix
        from config import USER_PROFILE_PLACEHOLDER_SUFFIX as suffix
        
        if not prefix or not suffix or prefix not in template_content:
            return template_content
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"替换用户资料占位符时未找到用户: {user_id}")
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
                        replacements[f"{prefix}{key}{suffix}"] = str(value)
            except Exception as e:
                logger.error(f"解析用户资料JSON数据失败: {str(e)}")
        
        result = template_content
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
