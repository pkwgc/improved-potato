"""
订单处理模块 - 处理从聊天中提取订单信息并创建订单

此模块提供以下功能：
1. 从AI回复中提取订单信息
2. 创建订单并减少库存
3. 获取用户订单列表
"""

import json
import logging
import re
import random
import string
from datetime import datetime
from sqlalchemy import desc
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def extract_order_from_ai_response(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """从AI回复中提取订单信息
    
    Args:
        response: AI回复的JSON数据
        
    Returns:
        订单信息字典，如果没有则返回None
    """
    try:
        if not response or not isinstance(response, dict):
            return None
            
        trigger_api = response.get("trigger_api", False)
        intent = response.get("intent", "")
        
        if trigger_api and intent == "购买商品":
            logger.info("检测到明确的购买商品意图")
            
            slots = response.get("slots", {})
            if slots:
                product_id = slots.get("product_id", "")
                quantity_str = slots.get("quantity", "1")
                price_str = slots.get("price", "0")
                delivery = slots.get("delivery", "")
                
                try:
                    quantity = int(quantity_str)
                except ValueError:
                    quantity = 1
                    
                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0
                
                return {
                    "products": [{
                        "name": product_id,  # 使用product_id作为商品名称
                        "id": product_id,
                        "quantity": quantity,
                        "price": price
                    }],
                    "status": "pending",
                    "delivery_address": delivery
                }
        
        raw_content = response.get("raw_content", "")
        reply = response.get("reply", "")
        
        order_data = None
        if raw_content:
            try:
                match = re.search(r'{.*}', raw_content, re.DOTALL)
                if match:
                    json_str = re.sub(r'(?<!\\)\\(?![\\/"bfnrtu])', r'\\\\', match.group())
                    parsed = json.loads(json_str)
                    
                    if "order" in parsed:
                        order_data = parsed["order"]
                    elif "order_info" in parsed:
                        order_data = parsed["order_info"]
                    elif "slots" in parsed and parsed.get("intent") == "购买商品":
                        slots = parsed.get("slots", {})
                        product_id = slots.get("product_id", "")
                        quantity_str = slots.get("quantity", "1")
                        price_str = slots.get("price", "0")
                        delivery = slots.get("delivery", "")
                        
                        try:
                            quantity = int(quantity_str)
                        except ValueError:
                            quantity = 1
                            
                        try:
                            price = float(price_str)
                        except ValueError:
                            price = 0.0
                        
                        order_data = {
                            "products": [{
                                "name": product_id,
                                "id": product_id,
                                "quantity": quantity,
                                "price": price
                            }],
                            "status": "pending",
                            "delivery_address": delivery
                        }
            except Exception as e:
                logger.warning(f"从原始回复中提取订单信息失败: {str(e)}")
        
        if not order_data and reply:
            order_success_keywords = ["下单成功", "订单已创建", "已为您下单", "已完成下单", "订单已生成", 
                                     "购买成功", "已购买", "已帮您购买", "已帮您下单", "已锁定"]
            if any(keyword in reply for keyword in order_success_keywords):
                products = []
                
                product_pattern = r'([^，。！？,.!?]*?(?:商品|产品|款)[^，。！？,.!?]*?)(?:，|。|！|？|,|.|!|\?|$)'
                product_matches = re.finditer(product_pattern, reply)
                
                for match in product_matches:
                    product_text = match.group(1)
                    name_match = re.search(r'([\u4e00-\u9fa5A-Za-z0-9]+(?:手机|电脑|平板|手表|耳机|商品|产品|款)[\u4e00-\u9fa5A-Za-z0-9]*)', product_text)
                    quantity_match = re.search(r'(\d+)(?:件|个|台|部|只)', product_text)
                    
                    if name_match:
                        product_name = name_match.group(1)
                        quantity = int(quantity_match.group(1)) if quantity_match else 1
                        
                        products.append({
                            "name": product_name,
                            "quantity": quantity
                        })
                
                if not products:
                    simple_product_match = re.search(r'(\d+)(?:件|个|台|部|只)\s*([A-Za-z0-9\u4e00-\u9fa5]+)(?:款|型号)?', reply)
                    if simple_product_match:
                        quantity = int(simple_product_match.group(1))
                        product_name = simple_product_match.group(2)
                        products.append({
                            "name": product_name,
                            "quantity": quantity
                        })
                
                if products:
                    order_data = {
                        "products": products,
                        "status": "pending"
                    }
        
        return order_data
    except Exception as e:
        logger.error(f"提取订单信息出错: {str(e)}")
        return None

def create_order_from_chat(db, user_id: str, ai_response: Dict[str, Any]) -> Optional[Any]:
    """从聊天回复中创建订单
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        ai_response: AI回复的JSON数据
        
    Returns:
        创建的订单对象，如果创建失败则返回None
    """
    try:
        logger.info(f"尝试从聊天回复中创建订单: user_id={user_id}")
        
        order_data = extract_order_from_ai_response(ai_response)
        if not order_data:
            logger.info(f"未从AI回复中提取到订单信息: user_id={user_id}")
            return None
            
        from database import User, Order, OrderItem, InventoryItem
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"用户不存在: {user_id}")
            return None
            
        contact_info = ""
        address = order_data.get("delivery_address", "")
        if not address and hasattr(user, 'profile_data') and user.profile_data:
            try:
                profile = json.loads(user.profile_data)
                if "contact_info" in profile:
                    contact = profile["contact_info"]
                    name = contact.get("name", "")
                    phone = contact.get("phone", "")
                    address = contact.get("address", "")
                    
                    if name or phone or address:
                        contact_parts = []
                        if name:
                            contact_parts.append(f"姓名: {name}")
                        if phone:
                            contact_parts.append(f"电话: {phone}")
                        if address:
                            contact_parts.append(f"地址: {address}")
                            
                        contact_info = ", ".join(contact_parts)
            except Exception as e:
                logger.error(f"解析用户资料出错: {str(e)}")
        
        order_number = generate_order_number()
        
        new_order = Order(
            user_id=user.id,
            order_number=order_number,
            status="pending",
            payment_status="unpaid",
            contact_info=contact_info,
            shipping_address=address,
            notes=f"从聊天中创建的订单，用户ID: {user_id}"
        )
        
        db.add(new_order)
        db.flush()  # 获取new_order.id
        
        total_amount = 0.0
        products = order_data.get("products", [])
        
        for product in products:
            product_name = product.get("name", "")
            product_id = product.get("id", "")
            quantity = product.get("quantity", 1)
            
            inventory_item = None
            if product_id:
                inventory_item = db.query(InventoryItem).filter(
                    InventoryItem.product_id == product_id
                ).order_by(InventoryItem.updated_at.desc()).first()
            
            if not inventory_item and product_name:
                inventory_item = db.query(InventoryItem).filter(
                    InventoryItem.product_name.like(f"%{product_name}%")
                ).order_by(InventoryItem.updated_at.desc()).first()
            
            price = product.get("price", 0.0)
            if inventory_item:
                price = inventory_item.price or price
                
                if inventory_item.quantity is not None:
                    inventory_item.quantity = max(0, inventory_item.quantity - quantity)
                    inventory_item.updated_at = datetime.utcnow()
                    logger.info(f"更新商品库存: {inventory_item.product_name}, 新数量: {inventory_item.quantity}")
            
            item_total = price * quantity
            total_amount += item_total
            
            order_item = OrderItem(
                order_id=new_order.id,
                product_name=product_name,
                product_id=product_id,
                quantity=quantity,
                price=price,
                total_price=item_total
            )
            
            db.add(order_item)
            
            from database import Sale
            sale = Sale(
                user_id=user.id,
                order_id=new_order.id,
                product_name=product_name,
                product_id=product_id,
                quantity=quantity,
                price=price,
                total_amount=item_total,
                payment_method="未支付",
                notes=f"订单号: {order_number}"
            )
            
            db.add(sale)
        
        new_order.total_amount = total_amount
        
        db.commit()
        logger.info(f"成功创建订单: {order_number}, 总金额: {total_amount}, 商品数: {len(products)}")
        
        return new_order
    except Exception as e:
        logger.error(f"创建订单出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        return None

def get_user_orders(db, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """获取用户的订单列表
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        limit: 返回的最大订单数量
        
    Returns:
        订单列表
    """
    try:
        from database import User, Order, OrderItem
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"用户不存在: {user_id}")
            return []
            
        orders = db.query(Order).filter(
            Order.user_id == user.id
        ).order_by(Order.created_at.desc()).limit(limit).all()
        
        result = []
        for order in orders:
            order_items = db.query(OrderItem).filter(
                OrderItem.order_id == order.id
            ).all()
            
            items = []
            for item in order_items:
                items.append({
                    "product_name": item.product_name,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.price,
                    "total_price": item.total_price
                })
            
            result.append({
                "order_number": order.order_number,
                "total_amount": order.total_amount,
                "status": order.status,
                "payment_status": order.payment_status,
                "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "items": items
            })
            
        return result
    except Exception as e:
        logger.error(f"获取用户订单出错: {str(e)}")
        return []

def generate_order_number():
    """生成唯一的订单号"""
    prefix = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{random_part}"
