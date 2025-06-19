@echo off
REM 微信朋友圈AI画像系统启动脚本

echo 🚀 启动微信朋友圈AI画像系统...

REM 设置SQLite模式
set USE_SQLITE=true

REM 检查Python依赖
echo 📦 检查依赖包...
pip install -r requirements.txt

REM 启动Flask应用
echo 🔥 启动Flask应用...
python app.py
