from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, session
from flask_login import login_required, current_user
import logging
import traceback
import os

# Create blueprint
main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    """Main route that serves the landing page."""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        return render_template('error.html',
                           error_name='Internal Server Error',
                           error_code=500,
                           error_description='An error occurred while loading the page.',
                           error_details=traceback.format_exc() if current_app.config.get('DEBUG') else None), 500

@main_bp.route('/screener')
@login_required
def screener():
    """Stock screener route."""
    try:
        # Check if the screener template exists
        template_path = os.path.join(current_app.root_path, 'templates', 'screener.html')
        if not os.path.exists(template_path):
            logger.error(f"Screener template not found at {template_path}")
            return render_template('error.html',
                               error_name='Page Not Found',
                               error_code=404,
                               error_description='The screener page is currently unavailable.'), 404
        
        return render_template('screener.html')
        
    except Exception as e:
        logger.error(f"Error in screener route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        return render_template('error.html',
                           error_name='Internal Server Error',
                           error_code=500,
                           error_description='An error occurred while loading the screener.',
                           error_details=traceback.format_exc() if current_app.config.get('DEBUG') else None), 500

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard route."""
    try:
        # Get user-specific data
        user_data = {
            'username': current_user.username,
            'email': current_user.email,
            'user_data': current_user.user_data
        }
        
        return render_template('dash.html', **user_data)
        
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/profile')
@login_required
def profile():
    """User profile route."""
    try:
        return render_template('profile.html', user=current_user)
    except Exception as e:
        logger.error(f"Error in profile route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading your profile.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/settings')
@login_required
def settings():
    """User settings route."""
    try:
        return render_template('settings.html')
    except Exception as e:
        logger.error(f"Error in settings route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading settings.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/about')
def about():
    """About page route."""
    try:
        return render_template('about.html')
    except Exception as e:
        logger.error(f"Error in about route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading the about page.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page route."""
    try:
        if request.method == 'POST':
            # Process contact form submission
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            message = request.form.get('message', '').strip()
            
            # Basic validation
            if not all([name, email, message]):
                flash('Please fill in all required fields.', 'error')
                return render_template('contact.html', 
                                    name=name, 
                                    email=email, 
                                    message=message)
            
            # Here you would typically send an email or save the contact form data
            # For now, we'll just log it
            logger.info(f"Contact form submitted - Name: {name}, Email: {email}, Message: {message[:100]}...")
            
            flash('Thank you for your message. We will get back to you soon!', 'success')
            return redirect(url_for('main.contact'))
            
        return render_template('contact.html')
        
    except Exception as e:
        logger.error(f"Error in contact route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while processing your request.', 'error')
        return redirect(url_for('main.contact'))

@main_bp.route('/privacy-policy')
def privacy_policy():
    """Privacy policy page route."""
    try:
        return render_template('privacy_policy.html')
    except Exception as e:
        logger.error(f"Error in privacy policy route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading the privacy policy.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/terms-of-service')
def terms_of_service():
    """Terms of service page route."""
    try:
        return render_template('terms_of_service.html')
    except Exception as e:
        logger.error(f"Error in terms of service route: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while loading the terms of service.', 'error')
        return redirect(url_for('main.index'))

# Error handlers
@main_bp.app_errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@main_bp.app_errorhandler(403)
def forbidden(e):
    """Handle 403 errors."""
    return render_template('errors/403.html'), 403

@main_bp.app_errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors."""
    return render_template('errors/500.html'), 500
