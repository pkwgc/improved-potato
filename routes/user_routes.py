"""
User Routes for WeChat AI Chatbot System
Handles all user-related endpoints
"""
import os
import json
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
from database import get_db, User, Template, UserTemplateBinding, ChatMessage, verify_password
from services.chat_service import ChatService
from services.inventory_service import InventoryService
from services.order_service import OrderService

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def home():
    """Home page - redirect to user login"""
    return redirect(url_for('user.user_login'))

@user_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    """User login"""
    if request.method == 'POST':
        user_id = request.form.get('user_id') or request.form.get('username')
        password = request.form.get('password')
        
        if not user_id:
            flash('User ID is required')
            return render_template('user_login.html')
        
        if not password:
            flash('Password is required')
            return render_template('user_login.html')
        
        try:
            db = next(get_db())
            user = db.query(User).filter(User.user_id == user_id).first()
            
            logger.info(f"Login attempt for user_id: {user_id}")
            logger.info(f"User found: {user is not None}")
            if user:
                logger.info(f"User has password: {user.password is not None}")
                logger.info(f"Password verification: {verify_password(password, user.password) if user.password else 'No password set'}")
            
            if user and user.password and verify_password(password, user.password):
                session['user_id'] = user_id
                session['username'] = user.username
                db.close()
                logger.info(f"Login successful for user: {user_id}")
                return redirect(url_for('user.user_dashboard'))
            else:
                flash('Invalid user ID or password')
                logger.info(f"Login failed for user: {user_id}")
                db.close()
        except Exception as e:
            logger.error(f"User login error: {str(e)}")
            flash('Login error occurred')
    
    return render_template('user_login.html')

@user_bp.route('/logout')
def user_logout():
    """User logout"""
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('user.user_login'))

@user_bp.route('/dashboard')
def user_dashboard():
    """User dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        bound_template = db.query(UserTemplateBinding).filter(
            UserTemplateBinding.user_id == user.id
        ).first()
        
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id
        ).order_by(ChatMessage.created_at.desc()).limit(5).all()
        
        db.close()
        
        return render_template('user_dashboard.html',
                             user=user,
                             bound_template=bound_template,
                             recent_messages=recent_messages)
    except Exception as e:
        logger.error(f"User dashboard error: {str(e)}")
        return f"Error loading dashboard: {str(e)}", 500

@user_bp.route('/chat_history')
def user_chat_history():
    """User chat history"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        chat_service = ChatService()
        
        page = request.args.get('page', 1, type=int)
        limit = 20
        
        history = chat_service.get_chat_history(user_id, limit * page)
        
        return render_template('user_chat_history.html',
                             history=history,
                             page=page)
    except Exception as e:
        logger.error(f"User chat history error: {str(e)}")
        return f"Error loading chat history: {str(e)}", 500

@user_bp.route('/inventory')
def user_inventory():
    """User inventory management"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        inventory_service = InventoryService()
        
        inventory = inventory_service.get_user_inventory(user_id)
        
        return render_template('user_inventory.html',
                             inventory=inventory)
    except Exception as e:
        logger.error(f"User inventory error: {str(e)}")
        return f"Error loading inventory: {str(e)}", 500

@user_bp.route('/orders')
def user_orders():
    """User orders"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        order_service = OrderService()
        
        orders = order_service.get_user_orders(user_id)
        
        return render_template('user_orders.html',
                             orders=orders)
    except Exception as e:
        logger.error(f"User orders error: {str(e)}")
        return f"Error loading orders: {str(e)}", 500

@user_bp.route('/templates')
def user_templates():
    """User template selection"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        templates = db.query(Template).filter(Template.is_active == True).all()
        
        current_binding = db.query(UserTemplateBinding).filter(
            UserTemplateBinding.user_id == user.id
        ).first()
        
        db.close()
        
        return render_template('user_templates.html',
                             templates=templates,
                             current_binding=current_binding)
    except Exception as e:
        logger.error(f"User templates error: {str(e)}")
        return f"Error loading templates: {str(e)}", 500

@user_bp.route('/token_packages')
def user_token_packages():
    """User token packages page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_token_packages.html', user=user)
    except Exception as e:
        logger.error(f"User token packages error: {str(e)}")
        return f"Error loading token packages: {str(e)}", 500

@user_bp.route('/sales')
def user_sales():
    """User sales statistics page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_sales.html', user=user)
    except Exception as e:
        logger.error(f"User sales error: {str(e)}")
        return f"Error loading sales: {str(e)}", 500

@user_bp.route('/contacts')
def user_contacts():
    """User contacts/WeChat management page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_contacts.html', user=user)
    except Exception as e:
        logger.error(f"User contacts error: {str(e)}")
        return f"Error loading contacts: {str(e)}", 500

@user_bp.route('/customer_management')
def user_customer_management():
    """User customer management page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_customer_management.html', user=user)
    except Exception as e:
        logger.error(f"User customer management error: {str(e)}")
        return f"Error loading customer management: {str(e)}", 500

@user_bp.route('/proactive_tracking')
def user_proactive_tracking():
    """User proactive tracking management page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_proactive_tracking.html', user=user)
    except Exception as e:
        logger.error(f"User proactive tracking error: {str(e)}")
        return f"Error loading proactive tracking: {str(e)}", 500

@user_bp.route('/instruction_approval')
def user_instruction_approval():
    """User instruction approval center page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_instruction_approval.html', user=user)
    except Exception as e:
        logger.error(f"User instruction approval error: {str(e)}")
        return f"Error loading instruction approval: {str(e)}", 500

@user_bp.route('/knowledge_management')
def user_knowledge_management():
    """User knowledge management page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_knowledge_management.html', user=user)
    except Exception as e:
        logger.error(f"User knowledge management error: {str(e)}")
        return f"Error loading knowledge management: {str(e)}", 500

@user_bp.route('/data_analytics')
def user_data_analytics():
    """User data analytics page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_data_analytics.html', user=user)
    except Exception as e:
        logger.error(f"User data analytics error: {str(e)}")
        return f"Error loading data analytics: {str(e)}", 500

@user_bp.route('/moments')
def user_moments():
    """User moments/social media management page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_moments.html', user=user)
    except Exception as e:
        logger.error(f"User moments error: {str(e)}")
        return f"Error loading moments: {str(e)}", 500

@user_bp.route('/profile')
def user_profile():
    """User profile management page"""
    if 'user_id' not in session:
        return redirect(url_for('user.user_login'))
    
    try:
        user_id = session['user_id']
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return redirect(url_for('user.user_login'))
        
        db.close()
        
        return render_template('user_profile.html', user=user)
    except Exception as e:
        logger.error(f"User profile error: {str(e)}")
        return f"Error loading profile: {str(e)}", 500

@user_bp.route('/api/bind_template', methods=['POST'])
def api_bind_template():
    """API to bind template to user"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user_id = session['user_id']
        data = request.get_json()
        template_id = data.get('template_id')
        
        if not template_id:
            return jsonify({"error": "Template ID is required"}), 400
        
        db = next(get_db())
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            db.close()
            return jsonify({"error": "User not found"}), 404
        
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            db.close()
            return jsonify({"error": "Template not found"}), 404
        
        existing_binding = db.query(UserTemplateBinding).filter(
            UserTemplateBinding.user_id == user.id
        ).first()
        
        if existing_binding:
            existing_binding.template_id = template_id
        else:
            new_binding = UserTemplateBinding(
                user_id=user.id,
                template_id=template_id
            )
            db.add(new_binding)
        
        db.commit()
        db.close()
        
        return jsonify({"message": "Template bound successfully"})
        
    except Exception as e:
        logger.error(f"Bind template error: {str(e)}")
        return jsonify({"error": str(e)}), 500
