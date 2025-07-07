"""
Third-party extensions initialization for WeChat AI Chatbot System
"""
import os
import threading
from flask import Flask
from flask_socketio import SocketIO

socketio = None

def init_extensions(app: Flask):
    """Initialize all third-party extensions"""
    global socketio
    
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
    
    from utils.helpers import register_template_filters
    register_template_filters(app)
    
    return socketio
