from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt
import logging
import traceback
import json
from datetime import datetime

# Import from app modules
from app.auth import User, authenticate_user, load_user, send_verification_email, confirm_verification_token
from app import db

# Create blueprint
auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    logger.info("Login route accessed")
    
    if current_user.is_authenticated:
        logger.info(f"User {current_user.username} is already logged in, redirecting to dashboard")
        return redirect(url_for('main.dashboard'))
    
    error = None
    
    if request.method == 'POST':
        logger.debug("Login form submitted")
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = True if request.form.get('remember') else False
        
        logger.debug(f"Login attempt - Username: {username}, Remember: {remember}")
        
        if not username or not password:
            error = 'Please enter both username and password'
            logger.warning("Login failed: Missing username or password")
        else:
            user = authenticate_user(username, password)
            
            if user and user.id is not None:
                login_success = login_user(user, remember=remember)
                
                if login_success:
                    logger.info(f"User {username} logged in successfully")
                    
                    # Update last login time
                    try:
                        with db.get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("""
                                    UPDATE users 
                                    SET user_data = jsonb_set(
                                        user_data,
                                        '{account,last_login}',
                                        to_jsonb(now() AT TIME ZONE 'UTC')
                                    )
                                    WHERE id = %s
                                    RETURNING user_data->'account'->'last_login'
                                """, (user.id,))
                                conn.commit()
                    except Exception as e:
                        logger.error(f"Error updating last login time: {str(e)}")
                    
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('main.dashboard'))
                else:
                    error = 'Login failed. Please try again.'
                    logger.warning(f"Login failed for user: {username}")
            else:
                error = 'Invalid username or password'
                logger.warning(f"Invalid login attempt for username: {username}")
    
    return render_template('login.html', error=error)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    logger.info("Registration route accessed")
    
    if current_user.is_authenticated:
        logger.info(f"User {current_user.username} is already logged in, redirecting to dashboard")
        return redirect(url_for('main.dashboard'))
    
    error = None
    
    if request.method == 'POST':
        logger.debug("Registration form submitted")
        
        # Get form data
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Basic validation
        if not all([email, password, confirm_password]):
            error = 'All fields are required'
            logger.warning("Registration failed: Missing required fields")
        elif password != confirm_password:
            error = 'Passwords do not match'
            logger.warning("Registration failed: Passwords do not match")
        elif len(password) < 8:
            error = 'Password must be at least 8 characters long'
            logger.warning("Registration failed: Password too short")
        else:
            try:
                with db.get_connection() as conn:
                    with conn.cursor() as cur:
                        # Check if email already exists
                        cur.execute("""
                            SELECT id FROM users 
                            WHERE user_data->'account'->>'email' = %s 
                            LIMIT 1
                        """, (email,))
                        
                        if cur.fetchone():
                            error = 'Email or username already registered'
                            logger.warning(f"Registration failed: Email {email} or username {username} already exists")
                        else:
                            # Hash password
                            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                            
                            # Create user data structure based on backup with misc1-10 added
                            user_data = {
                                'account': {
                                    'misc1': [],
                                    'misc2': [],
                                    'misc3': [],
                                    'misc4': [],
                                    'misc5': [],
                                    'misc6': [],
                                    'misc7': [],
                                    'misc8': [],
                                    'misc9': [],
                                    'misc10': [],
                                    'username': email,  # Use email as username
                                    'password': hashed_pw,
                                    'email': email,
                                    'profile': {
                                        'name': email,  # Use email as name
                                        'email': email,
                                        'premium': 'no',
                                        'gender': 'Prefer not to say'
                                    },
                                    'conditions': []
                                }
                            }
                            
                            # Insert new user
                            cur.execute("""
                                INSERT INTO users (user_data) 
                                VALUES (%s) 
                                RETURNING id
                            """, (json.dumps(user_data),))
                            
                            user_id = cur.fetchone()[0]
                            conn.commit()
                            
                            logger.info(f"New user registered - ID: {user_id}, Email: {email}")
                            
                            # Send verification email
                            if current_app.config.get('ENABLE_EMAIL_VERIFICATION', True):
                                send_verification_email(email, email)  # Using email as name
                                logger.info(f"Verification email sent to {email}")
                                return redirect(url_for('auth.verification_pending', email=email))
                            else:
                                # Auto-verify if email verification is disabled
                                user = User(id=user_id, username=email, password=hashed_pw, email=email)
                                login_user(user)
                                flash('Registration successful!', 'success')
                                return redirect(url_for('main.dashboard'))
            
            except Exception as e:
                conn.rollback()
                error = 'An error occurred during registration. Please try again.'
                logger.error(f"Error during registration: {str(e)}")
                logger.debug(f"Stack trace:\n{traceback.format_exc()}")
    
    return render_template('register.html', error=error)

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logger.info(f"User {current_user.username} logged out")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify user's email with the provided token."""
    try:
        email = confirm_verification_token(token)
        if not email:
            flash('The verification link is invalid or has expired.', 'error')
            return redirect(url_for('auth.login'))
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Find user by email
                cur.execute("""
                    SELECT id, user_data FROM users 
                    WHERE user_data->'account'->'profile'->>'email' = %s 
                    LIMIT 1
                """, (email,))
                
                user_data = cur.fetchone()
                
                if not user_data:
                    flash('User not found.', 'error')
                    return redirect(url_for('auth.login'))
                
                user_id, user_json = user_data
                
                # Update email_verified status
                user_json['account']['email_verified'] = True
                
                # Update user in database
                cur.execute("""
                    UPDATE users 
                    SET user_data = %s 
                    WHERE id = %s
                """, (json.dumps(user_json), user_id))
                
                conn.commit()
                
                flash('Your email has been verified! You can now log in.', 'success')
                logger.info(f"Email verified for user ID: {user_id}")
                
                return redirect(url_for('auth.login'))
                
    except Exception as e:
        logger.error(f"Error verifying email: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while verifying your email. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/verification-pending')
def verification_pending():
    """Show verification pending page."""
    email = request.args.get('email', '')
    return render_template('auth/verification_pending.html', email=email)

@auth_bp.route('/resend-verification')
def resend_verification():
    """Resend verification email."""
    email = request.args.get('email', '').strip()
    if not email:
        flash('No email address provided.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Get user data
                cur.execute("""
                    SELECT user_data->'account'->>'username' as username
                    FROM users 
                    WHERE user_data->'account'->'profile'->>'email' = %s
                    LIMIT 1
                """, (email,))
                
                result = cur.fetchone()
                
                if not result:
                    flash('No account found with that email address.', 'error')
                    return redirect(url_for('auth.login'))
                
                username = result[0]
                
                # Resend verification email
                if send_verification_email(email, username):
                    flash('A new verification email has been sent. Please check your inbox.', 'info')
                else:
                    flash('Failed to send verification email. Please try again later.', 'error')
                
                return redirect(url_for('auth.verification_pending', email=email))
    
    except Exception as e:
        logger.error(f"Error resending verification email: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        flash('An error occurred while resending the verification email.', 'error')
        return redirect(url_for('auth.verification_pending', email=email))
