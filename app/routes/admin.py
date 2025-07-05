from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
import logging
import traceback
import json
from datetime import datetime

# Import from app modules
from app import db

# Create blueprint
admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

def admin_required(f):
    """
    Decorator to ensure the user is an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Check if user is authenticated and is admin
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
                
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT user_data->'account'->>'is_admin' as is_admin
                        FROM users 
                        WHERE id = %s
                    """, (current_user.id,))
                    
                    result = cur.fetchone()
                    
                    if not result or not result[0] or result[0].lower() != 'true':
                        flash('You do not have permission to access this page.', 'error')
                        return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Admin check failed: {str(e)}")
            logger.debug(f"Stack trace:\n{traceback.format_exc()}")
            flash('An error occurred while checking admin privileges.', 'error')
            return redirect(url_for('main.dashboard'))
    
    return decorated_function

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard route."""
    try:
        # Get basic stats
        stats = {}
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Get total users
                cur.execute("SELECT COUNT(*) FROM users")
                stats['total_users'] = cur.fetchone()[0]
                
                # Get active users (logged in last 30 days)
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM users 
                    WHERE (user_data->'account'->>'last_login')::timestamptz > NOW() - INTERVAL '30 days'
                """)
                stats['active_users'] = cur.fetchone()[0]
                
                # Get new users this month
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM users 
                    WHERE (user_data->'account'->>'created_at')::timestamptz > DATE_TRUNC('month', CURRENT_DATE)
                """)
                stats['new_users_this_month'] = cur.fetchone()[0]
        
        return render_template('admin/dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error in admin dashboard: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading the admin dashboard.', 'error')
        return redirect(url_for('main.dashboard'))

@admin_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    """Manage users page."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Get total users count
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                
                # Get paginated users
                offset = (page - 1) * per_page
                cur.execute("""
                    SELECT 
                        id,
                        user_data->'account'->>'username' as username,
                        user_data->'account'->'profile'->>'email' as email,
                        (user_data->'account'->>'created_at')::timestamptz as created_at,
                        (user_data->'account'->>'last_login')::timestamptz as last_login,
                        (user_data->'account'->>'is_admin')::boolean as is_admin,
                        (user_data->'account'->>'email_verified')::boolean as email_verified
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (per_page, offset))
                
                columns = [desc[0] for desc in cur.description]
                users = [dict(zip(columns, row)) for row in cur.fetchall()]
        
        return render_template(
            'admin/users.html',
            users=users,
            page=page,
            per_page=per_page,
            total_users=total_users
        )
        
    except Exception as e:
        logger.error(f"Error in manage users: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading users.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/user/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """View user details."""
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        user_data->'account' as account_data,
                        user_data->'account'->'profile' as profile_data,
                        (user_data->'account'->>'created_at')::timestamptz as created_at,
                        (user_data->'account'->>'last_login')::timestamptz as last_login
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
                
                user_data = cur.fetchone()
                
                if not user_data:
                    flash('User not found.', 'error')
                    return redirect(url_for('admin.manage_users'))
                
                # Convert to dict for easier access in template
                columns = [desc[0] for desc in cur.description]
                user = dict(zip(columns, user_data))
                
                # Parse JSON fields
                if isinstance(user.get('account_data'), str):
                    user['account_data'] = json.loads(user['account_data'])
                if isinstance(user.get('profile_data'), str):
                    user['profile_data'] = json.loads(user['profile_data'])
        
        return render_template('admin/view_user.html', user=user)
        
    except Exception as e:
        logger.error(f"Error viewing user {user_id}: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading user details.', 'error')
        return redirect(url_for('admin.manage_users'))

@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    """Admin settings page."""
    try:
        if request.method == 'POST':
            # Handle form submission
            setting_name = request.form.get('setting_name')
            setting_value = request.form.get('setting_value')
            
            # Here you would typically save the setting to a database
            # For now, we'll just log it
            logger.info(f"Admin setting updated - {setting_name}: {setting_value}")
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('admin.admin_settings'))
        
        # Get current settings (this is a placeholder)
        settings = {
            'site_name': 'Strong App',
            'registration_enabled': True,
            'email_verification_required': True,
            'maintenance_mode': False
        }
        
        return render_template('admin/settings.html', settings=settings)
        
    except Exception as e:
        logger.error(f"Error in admin settings: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading settings.', 'error')
        return redirect(url_for('admin.admin_dashboard'))
