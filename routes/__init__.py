"""
Routes package initialization
"""
from .admin_routes import admin_bp
from .api_routes import api_bp
from .user_routes import user_bp

def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/user')
