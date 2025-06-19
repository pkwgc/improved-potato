import os
import csv
import json
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from database import User, InventoryUpload

logger = logging.getLogger(__name__)

def process_inventory_file(file_path: str, user_id: str, upload_id: Optional[int] = None) -> Dict[str, Any]:
    """处理库存文件的便捷函数
    
    Args:
        file_path: 文件路径
        user_id: 用户ID
        upload_id: 上传记录ID，用于关联商品详情
        
    Returns:
        处理后的数据字典
    """
    try:
        logger.info(f"处理库存文件: {file_path}, user_id={user_id}, upload_id={upload_id}")
        processor = InventoryProcessor()
        result = processor.process_inventory_file(file_path, "inventory")
        
        if result and upload_id:
            try:
                from database import InventoryItem, get_db
                db = next(get_db())
                
                
                items = result.get("items", [])
                saved_count = 0
                
                for item in items:
                    name_keys = ["产品名称", "名称", "商品名称", "商品", "product_name", "name"]
                    quantity_keys = ["库存数量", "数量", "库存", "quantity", "stock"]
                    price_keys = ["单价", "价格", "price"]
                    id_keys = ["产品ID", "ID", "编号", "product_id", "id"]
                    
                    product_name = None
                    for k in name_keys:
                        if k in item:
                            product_name = item[k]
                            break
                    
                    product_id = None
                    for k in id_keys:
                        if k in item:
                            product_id = item[k]
                            break
                    
                    quantity = 0
                    for k in quantity_keys:
                        if k in item and item[k] is not None:
                            try:
                                quantity = int(item[k])
                                break
                            except (ValueError, TypeError):
                                pass
                    
                    price = None
                    for k in price_keys:
                        if k in item and item[k] is not None:
                            try:
                                price = float(item[k])
                                break
                            except (ValueError, TypeError):
                                pass
                    
                    total_price = None
                    if price is not None and quantity is not None:
                        total_price = price * quantity
                    
                    if product_name:
                        inventory_item = InventoryItem(
                            inventory_upload_id=upload_id,
                            product_name=product_name,
                            product_id=product_id,
                            quantity=quantity,
                            price=price,
                            total_price=total_price
                        )
                        db.add(inventory_item)
                        saved_count += 1
                
                db.commit()
                logger.info(f"已保存{saved_count}条商品记录到数据库")
                
            except Exception as e:
                logger.error(f"保存商品详情出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        if result:
            return {
                "count": result.get("total_items", 0),
                "summary": result.get("summary", ""),
                "items": result.get("items", [])
            }
        else:
            return {"count": 0, "summary": "处理失败", "items": []}
    except Exception as e:
        logger.error(f"处理库存文件出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"count": 0, "summary": f"处理出错: {str(e)}", "items": []}

class InventoryProcessor:
    """处理用户上传的库存文件，提取库存数据"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        logger.info(f"初始化InventoryProcessor，上传目录: {upload_dir}")
    
    def process_inventory_file(self, file_path: str, inventory_type: str = "inventory") -> Optional[Dict[str, Any]]:
        """处理库存文件，返回处理后的数据
        
        Args:
            file_path: 文件路径
            inventory_type: 文件类型，'inventory'或'product'
            
        Returns:
            处理后的数据字典，如果处理失败则返回None
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            file_ext = os.path.splitext(file_path)[1].lower()
            logger.info(f"处理库存文件: {file_path}, 类型: {inventory_type}, 扩展名: {file_ext}")
            
            if file_ext in ['.csv']:
                return self._process_csv(file_path, inventory_type)
            elif file_ext in ['.xlsx', '.xls']:
                return self._process_excel(file_path, inventory_type)
            else:
                logger.error(f"不支持的文件格式: {file_ext}")
                return None
        except Exception as e:
            logger.error(f"处理库存文件出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _process_csv(self, file_path: str, inventory_type: str) -> Optional[Dict[str, Any]]:
        """处理CSV文件"""
        try:
            logger.info(f"处理CSV文件: {file_path}")
            df = pd.read_csv(file_path, encoding='utf-8')
            logger.info(f"CSV文件列: {df.columns.tolist()}")
            return self._process_dataframe(df, inventory_type)
        except UnicodeDecodeError:
            try:
                logger.info(f"尝试使用GBK编码读取CSV文件: {file_path}")
                df = pd.read_csv(file_path, encoding='gbk')
                logger.info(f"CSV文件列: {df.columns.tolist()}")
                return self._process_dataframe(df, inventory_type)
            except Exception as e:
                logger.error(f"处理CSV文件出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return None
        except Exception as e:
            logger.error(f"处理CSV文件出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _process_excel(self, file_path: str, inventory_type: str) -> Optional[Dict[str, Any]]:
        """处理Excel文件"""
        try:
            logger.info(f"处理Excel文件: {file_path}")
            df = pd.read_excel(file_path)
            logger.info(f"Excel文件列: {df.columns.tolist()}")
            return self._process_dataframe(df, inventory_type)
        except Exception as e:
            logger.error(f"处理Excel文件出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _process_dataframe(self, df: pd.DataFrame, inventory_type: str) -> Optional[Dict[str, Any]]:
        """处理数据框"""
        try:
            if inventory_type == "inventory":
                return self._process_inventory_data(df)
            elif inventory_type == "product":
                return self._process_product_data(df)
            else:
                logger.error(f"不支持的库存类型: {inventory_type}")
                return None
        except Exception as e:
            logger.error(f"处理数据框出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _process_inventory_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """处理库存数据"""
        required_columns = ["产品ID", "产品名称", "库存数量"]
        
        for col in required_columns:
            if col not in df.columns and col.lower() not in df.columns:
                similar_cols = [c for c in df.columns if any(rc.lower() in c.lower() for rc in [
                    "产品", "ID", "编号", "名称", "库存", "数量", "价格", "单价"
                ])]
                
                if not similar_cols:
                    logger.warning(f"缺少必要的列: {col}，无法找到类似的列")
                    continue
                
                logger.info(f"找到类似的列: {similar_cols}")
        
        inventory_data = []
        for _, row in df.iterrows():
            item = {}
            for col in df.columns:
                item[col] = row[col]
            inventory_data.append(item)
        
        summary = self._generate_inventory_summary(inventory_data)
        logger.info(f"生成库存摘要: {summary}")
        
        return {
            "type": "inventory",
            "items": inventory_data,
            "total_items": len(inventory_data),
            "summary": summary
        }
    
    def _process_product_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """处理产品信息数据"""
        product_data = []
        for _, row in df.iterrows():
            item = {}
            for col in df.columns:
                item[col] = row[col]
            product_data.append(item)
        
        summary = self._generate_product_summary(product_data)
        logger.info(f"生成产品摘要: {summary}")
        
        return {
            "type": "product",
            "items": product_data,
            "total_items": len(product_data),
            "summary": summary
        }
    
    def _generate_inventory_summary(self, inventory_data: List[Dict[str, Any]]) -> str:
        """生成库存摘要"""
        if not inventory_data:
            logger.warning("没有库存数据，返回默认摘要")
            return "暂无库存数据"
        
        name_keys = ["产品名称", "名称", "商品名称", "商品", "product_name", "name"]
        quantity_keys = ["库存数量", "数量", "库存", "quantity", "stock"]
        price_keys = ["单价", "价格", "price"]
        notes_keys = ["备注", "notes", "description", "描述", "说明"]
        
        name_key = None
        for k in name_keys:
            for col in inventory_data[0].keys():
                if k.lower() == col.lower():
                    name_key = col
                    break
            if name_key:
                break
                
        quantity_key = None
        for k in quantity_keys:
            for col in inventory_data[0].keys():
                if k.lower() == col.lower():
                    quantity_key = col
                    break
            if quantity_key:
                break
                
        price_key = None
        for k in price_keys:
            for col in inventory_data[0].keys():
                if k.lower() == col.lower():
                    price_key = col
                    break
            if price_key:
                break
                
        notes_key = None
        for k in notes_keys:
            for col in inventory_data[0].keys():
                if k.lower() == col.lower():
                    notes_key = col
                    break
            if notes_key:
                break
        
        logger.info(f"找到的列: 名称={name_key}, 数量={quantity_key}, 价格={price_key}, 备注={notes_key}")
        
        if not name_key or not quantity_key:
            keys = list(inventory_data[0].keys())
            name_key = keys[0] if len(keys) > 0 else None
            quantity_key = keys[1] if len(keys) > 1 else None
            logger.warning(f"未找到标准列名，使用默认列: 名称={name_key}, 数量={quantity_key}")
        
        if not name_key or not quantity_key:
            logger.warning(f"无法确定名称和数量列，返回简单摘要")
            return f"共有{len(inventory_data)}件商品库存"
        
        summary_items = []
        for item in inventory_data[:10]:  # 只取前10个商品
            name = str(item.get(name_key, "未知商品"))
            quantity = item.get(quantity_key, 0)
            price_info = ""
            notes_info = ""
            
            if price_key:
                price = item.get(price_key, "")
                if price:
                    price_info = f"单价{price}元"
            
            if notes_key:
                notes = item.get(notes_key, "")
                if notes:
                    notes_info = f"备注: {notes}"
            
            item_summary = f"{name}: {quantity}件"
            if price_info:
                item_summary += f", {price_info}"
            if notes_info:
                item_summary += f", {notes_info}"
            
            summary_items.append(item_summary)
        
        summary = "、".join(summary_items)
        if len(inventory_data) > 10:
            summary += f"等共{len(inventory_data)}件商品"
        
        logger.info(f"生成的库存摘要: {summary}")
        return summary
    
    def _generate_product_summary(self, product_data: List[Dict[str, Any]]) -> str:
        """生成产品信息摘要"""
        if not product_data:
            logger.warning("没有产品数据，返回默认摘要")
            return "暂无产品信息"
        
        name_keys = ["产品名称", "名称", "商品名称", "商品", "product_name", "name"]
        
        name_key = None
        for k in name_keys:
            for col in product_data[0].keys():
                if k.lower() == col.lower():
                    name_key = col
                    break
            if name_key:
                break
        
        logger.info(f"找到的列: 名称={name_key}")
        
        if not name_key:
            keys = list(product_data[0].keys())
            name_key = keys[0] if len(keys) > 0 else None
            logger.warning(f"未找到标准列名，使用默认列: 名称={name_key}")
        
        if not name_key:
            logger.warning(f"无法确定名称列，返回简单摘要")
            return f"共有{len(product_data)}件商品信息"
        
        summary_items = []
        for item in product_data[:10]:  # 只取前10个商品
            name = str(item.get(name_key, "未知商品"))
            summary_items.append(name)
        
        summary = "、".join(summary_items)
        if len(product_data) > 10:
            summary += f"等共{len(product_data)}件商品"
        
        logger.info(f"生成的产品摘要: {summary}")
        return summary

def get_user_inventory(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """获取用户的库存数据
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        用户的库存数据，如果没有则返回None
    """
    try:
        logger.info(f"获取用户库存数据: user_id={user_id}")
        from database import User, InventoryUpload
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"用户不存在: {user_id}")
            return None
        
        latest_inventory = db.query(InventoryUpload).filter(
            InventoryUpload.user_id == user.id,
            InventoryUpload.type == "inventory",
            InventoryUpload.status == "success"
        ).order_by(InventoryUpload.created_at.desc()).first()
        
        if not latest_inventory:
            logger.info(f"用户没有上传库存: {user_id}")
            return None
        
        logger.info(f"找到用户最新库存: {latest_inventory.file_path}")
        
        if not os.path.exists(latest_inventory.file_path):
            logger.warning(f"库存文件不存在: {latest_inventory.file_path}")
            return None
        
        processor = InventoryProcessor()
        inventory_data = processor.process_inventory_file(
            latest_inventory.file_path, 
            latest_inventory.type
        )
        
        if inventory_data:
            logger.info(f"成功处理用户库存数据: {inventory_data.get('summary', '')}")
        else:
            logger.warning(f"处理用户库存数据失败")
            
        return inventory_data
    except Exception as e:
        logger.error(f"获取用户库存出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_user_inventory_from_db(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """从数据库获取用户的库存数据
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        用户的库存数据，如果没有则返回None
    """
    try:
        logger.info(f"从数据库获取用户库存数据: user_id={user_id}")
        from database import User, InventoryUpload, InventoryItem
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"用户不存在: {user_id}")
            return None
        
        inventory_items = db.query(InventoryItem).join(InventoryUpload).filter(
            InventoryUpload.user_id == user.id,
            InventoryUpload.status == 'success'
        ).order_by(InventoryItem.updated_at.desc()).all()

        latest_items = {}
        for item in inventory_items:
            if item.product_id:
                if item.product_id not in latest_items or item.updated_at > latest_items[item.product_id].updated_at:
                    latest_items[item.product_id] = item
            else:
                key = f"name_{item.product_name}"
                if key not in latest_items or item.updated_at > latest_items[key].updated_at:
                    latest_items[key] = item

        inventory_items = list(latest_items.values())
        
        if not inventory_items:
            logger.info(f"用户库存为空: {user_id}")
            return None
        
        items = []
        for item in inventory_items:
            item_data = {
                "产品名称": item.product_name,
                "产品ID": item.product_id,
                "库存数量": item.quantity,
                "单价": item.price,
                "总价": item.total_price,
                "备注": item.notes
            }
            items.append(item_data)
        
        processor = InventoryProcessor()
        summary = processor._generate_inventory_summary(items)
        
        inventory_data = {
            "type": "inventory",
            "items": items,
            "summary": summary
        }
        
        logger.info(f"成功从数据库获取用户库存数据: {summary}")
        return inventory_data
    except Exception as e:
        logger.error(f"从数据库获取用户库存出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_user_product_info(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """获取用户的产品信息
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        用户的产品信息，如果没有则返回None
    """
    try:
        logger.info(f"获取用户产品信息: user_id={user_id}")
        from database import User, InventoryUpload
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"用户不存在: {user_id}")
            return None
        
        latest_product = db.query(InventoryUpload).filter(
            InventoryUpload.user_id == user.id,
            InventoryUpload.type == "product",
            InventoryUpload.status == "success"
        ).order_by(InventoryUpload.created_at.desc()).first()
        
        if not latest_product:
            logger.info(f"用户没有上传产品信息: {user_id}")
            return None
        
        logger.info(f"找到用户最新产品信息: {latest_product.file_path}")
        
        if not os.path.exists(latest_product.file_path):
            logger.warning(f"产品信息文件不存在: {latest_product.file_path}")
            return None
        
        processor = InventoryProcessor()
        product_data = processor.process_inventory_file(
            latest_product.file_path, 
            latest_product.type
        )
        
        if product_data:
            logger.info(f"成功处理用户产品信息: {product_data.get('summary', '')}")
        else:
            logger.warning(f"处理用户产品信息失败")
            
        return product_data
    except Exception as e:
        logger.error(f"获取用户产品信息出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_user_product_info_from_db(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """从数据库获取用户的产品信息
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        用户的产品信息，如果没有则返回None
    """
    try:
        logger.info(f"从数据库获取用户产品信息: user_id={user_id}")
        from database import User, InventoryUpload, InventoryItem
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"用户不存在: {user_id}")
            return None
        
        product_items = db.query(InventoryItem).join(InventoryUpload).filter(
            InventoryUpload.user_id == user.id,
            InventoryUpload.type == "product",
            InventoryUpload.status == 'success'
        ).order_by(InventoryItem.updated_at.desc()).all()

        latest_items = {}
        for item in product_items:
            if item.product_id:
                if item.product_id not in latest_items or item.updated_at > latest_items[item.product_id].updated_at:
                    latest_items[item.product_id] = item
            else:
                key = f"name_{item.product_name}"
                if key not in latest_items or item.updated_at > latest_items[key].updated_at:
                    latest_items[key] = item

        product_items = list(latest_items.values())
        
        if not product_items:
            logger.info(f"用户产品为空: {user_id}")
            return None
        
        items = []
        for item in product_items:
            item_data = {
                "产品名称": item.product_name,
                "产品ID": item.product_id,
                "库存数量": item.quantity,
                "单价": item.price,
                "总价": item.total_price,
                "备注": item.notes
            }
            items.append(item_data)
        
        processor = InventoryProcessor()
        summary = processor._generate_product_summary(items)
        
        product_data = {
            "type": "product",
            "items": items,
            "summary": summary
        }
        
        logger.info(f"成功从数据库获取用户产品信息: {summary}")
        return product_data
    except Exception as e:
        logger.error(f"从数据库获取用户产品信息出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def process_personalized_prompt_template(template: str, user_data: Dict[str, Any]) -> str:
    """
    处理个性化提示词模板，使用统一的占位符替换函数
    
    Args:
        template: 个性化提示词模板
        user_data: 用户数据字典
    
    Returns:
        处理后的提示词
    """
    try:
        from config import fill_placeholders
        import re
        
        logger.info(f"开始处理个性化提示词模板，用户数据键: {list(user_data.keys())}")
        
        if "user_input" not in user_data:
            user_data["user_input"] = "{user_input}"
            logger.info("添加user_input占位符")
        
        result = fill_placeholders(template, user_data)
        
        lines = result.split('\n')
        processed_lines = []
        user_info_added = False
        product_info_added = False
        user_info_section = False
        product_info_section = False
        
        for line in lines:
            if "【用户信息】" in line:
                user_info_section = True
                product_info_section = False
                processed_lines.append(line)
                continue
            
            if "【商品信息】" in line or "【库存信息】" in line:
                user_info_section = False
                product_info_section = True
                processed_lines.append(line)
                continue
            
            if line.strip() and line.strip()[0] == "【" and "】" in line:
                user_info_section = False
                product_info_section = False
            
            if user_info_section:
                if line.strip() and not re.search(r'\{[^}]+\}', line):
                    user_info_added = True
                processed_lines.append(line)
            elif product_info_section:
                if line.strip() and not re.search(r'\{[^}]+\}', line):
                    product_info_added = True
                processed_lines.append(line)
            else:
                processed_lines.append(line)
        
        if not user_info_added:
            logger.info("用户信息部分没有有效内容，移除整个部分")
            processed_lines = _remove_empty_section(processed_lines, "【用户信息】")
        
        if not product_info_added:
            logger.info("商品信息部分没有有效内容，移除整个部分")
            processed_lines = _remove_empty_section(processed_lines, "【商品信息】")
            processed_lines = _remove_empty_section(processed_lines, "【库存信息】")
        
        result = '\n'.join(processed_lines)
        logger.info(f"处理后的提示词: {result[:100]}...")
        return result
    except Exception as e:
        logger.error(f"处理个性化提示词模板出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return template

def _remove_empty_section(lines: list, section_name: str) -> list:
    """移除空的信息部分"""
    new_lines = []
    skip_section = False
    for line in lines:
        if section_name in line:
            skip_section = True
            continue
        
        if skip_section and (line.strip() == "" or (line.strip() and line.strip()[0] == "【" and "】" in line)):
            skip_section = False
        
        if not skip_section:
            new_lines.append(line)
    
    return new_lines

def debug_inventory_items_with_notes(db: Session, user_id: str) -> None:
    """调试函数：检查用户的库存商品中是否包含备注信息
    
    Args:
        db: 数据库会话
        user_id: 用户ID
    """
    try:
        logger.info(f"调试用户库存商品备注: user_id={user_id}")
        from database import User, InventoryUpload, InventoryItem
        
        inventory_data = get_user_inventory_from_db(db, user_id)
        if inventory_data and "items" in inventory_data:
            items_with_notes = [item for item in inventory_data["items"] if item.get("备注")]
            logger.info(f"用户有{len(items_with_notes)}/{len(inventory_data['items'])}件商品包含备注信息")
            
            for item in items_with_notes[:5]:  # 只显示前5个
                logger.info(f"商品备注示例: {item.get('产品名称', '')}: {item.get('备注', '')}")
    except Exception as e:
        logger.error(f"调试库存商品备注失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
