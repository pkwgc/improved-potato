#!/bin/bash

# 切换到项目目录
cd /home/ubuntu/workspace/optimized_system

# 创建必要的目录
mkdir -p logs uploads chat_records

# 安装依赖
pip install -r requirements.txt
pip install flask-socketio==5.3.6 pillow==10.0.0 jsonschema
pip install sqlalchemy==1.4.46 flask-sqlalchemy==2.5.1

echo "USE_SQLITE=true
SECRET_KEY=demo_secret_key_2025
DEBUG=true" > .env

# 运行数据库迁移脚本
python update_db.py

# 创建演示账户和数据
python create_demo_admin.py
python create_demo_data.py

# 启动应用
python app.py
