#!/bin/bash

echo "🚀 启动微信朋友圈AI画像系统..."

export USE_SQLITE=true

echo "📦 检查依赖包..."
pip install -r requirements.txt

echo "🔥 启动Flask应用..."
python app.py
