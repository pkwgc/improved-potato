
"""
配置应用使用SQLite数据库
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def configure_sqlite():
    """配置应用使用SQLite数据库"""
    try:
        os.environ['USE_SQLITE'] = 'true'
        
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        if "sqlite:///test.db" in config_content:
            logger.info("SQLite已配置，无需修改")
            return True
        
        if "DATABASE_URL = " in config_content:
            lines = config_content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith("DATABASE_URL = "):
                    lines[i] = "DATABASE_URL = 'sqlite:///test.db'"
                    break
            
            new_config = '\n'.join(lines)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_config)
            
            logger.info("成功配置SQLite数据库")
            return True
        else:
            logger.error("未找到DATABASE_URL配置项")
            return False
    except Exception as e:
        logger.error(f"配置SQLite失败: {str(e)}")
        return False

if __name__ == "__main__":
    configure_sqlite()
    print("已配置使用SQLite数据库。请运行 python init_db.py 初始化数据库，然后运行 python app.py 启动应用。")
