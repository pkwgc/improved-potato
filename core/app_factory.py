"""
Application Factory Pattern for WeChat AI Chatbot System
Creates and configures the Flask application with all necessary components
"""
import os
from flask import Flask
from flask_socketio import SocketIO
from database import create_tables
from config import load_config_from_file
import logging

logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """Create and configure Flask application"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    app.secret_key = os.urandom(24)
    
    load_config_from_file()
    
    @app.route('/')
    def index():
        """Root route - redirect to user login"""
        from flask import redirect, url_for
        return "WeChat AI Chatbot System - SocketIO Precise Targeting"
    
    socketio = SocketIO(app, cors_allowed_origins="*", 
                       ping_timeout=60, ping_interval=25)
    
    from services.websocket_service import register_socketio_handlers
    register_socketio_handlers(socketio)
    
    from api_send_message import register_api_send_message
    register_api_send_message(app, socketio)
    
    create_tables()
    
    logger.info("Flask application created successfully")
    return app, socketio

def initialize_database():
    """Initialize database with required tables"""
    try:
        create_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False
