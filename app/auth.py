from flask import current_app, url_for, flash, redirect, request
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt
import logging
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
import json
import traceback

logger = logging.getLogger(__name__)

class User(UserMixin):
    """User class for authentication."""
    def __init__(self, id, username, password, email=''):
        try:
            self.id = int(id) if id is not None and str(id).strip() not in ['', 'id'] else None
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Invalid ID format: {id} (type: {type(id)}), using None")
            self.id = None
            
        self.username = username
        self.password = password
        self.email = email
        self._user_data = None
        
        logger.debug(f"Created User - ID: {self.id}, Username: {self.username}")
    
    def get_auth_token(self):
        """Generate a secure token for 'remember me' functionality."""
        from . import db
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'user_id': self.id})
    
    @property
    def user_data(self):
        """Lazy-load user data from the database."""
        if self._user_data is None and self.id is not None:
            from . import db
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute("""
                            SELECT user_data FROM users WHERE id = %s
                        """, (self.id,))
                        result = cur.fetchone()
                        if result:
                            self._user_data = result[0]
                    except Exception as e:
                        logger.error(f"Error loading user data: {str(e)}")
        return self._user_data or {}

def load_user(user_id):
    """Load a user by ID. Called by Flask-Login to get the user object."""
    logger.debug(f"Loading user with ID: {user_id}")
    
    if not user_id or user_id == 'None':
        logger.warning("No user ID provided")
        return None
    
    try:
        from . import db
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, username, password, 
                           COALESCE(user_data->'account'->'profile'->>'email', 
                                   user_data->'account'->>'email', '') as email
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
                
                user_data = cur.fetchone()
                
                if user_data:
                    user = User(
                        id=user_data[0],
                        username=user_data[1],
                        password=user_data[2],
                        email=user_data[3]
                    )
                    logger.debug(f"Successfully loaded user: {user.username} (ID: {user.id})")
                    return user
                else:
                    logger.warning(f"User not found with ID: {user_id}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        return None

def authenticate_user(username, password):
    """Authenticate a user with the given username/email and password."""
    logger.info(f"Authentication attempt for username/email: {username}")
    
    if not username or not password:
        logger.warning("Authentication failed: Empty username or password")
        return None
        
    try:
        from .models import db
        from sqlalchemy import text
        
        # Query the database using SQLAlchemy
        query = text("""
            SELECT 
                id, 
                user_data->'account'->>'username' as username,
                user_data->'account'->>'password' as password_hash,
                COALESCE(
                    user_data->'account'->'profile'->>'email', 
                    user_data->'account'->>'email', 
                    ''
                ) as email,
                user_data->'account' as account_data
            FROM users 
            WHERE user_data->'account'->>'email' = :username 
               OR user_data->'account'->>'username' = :username
            LIMIT 1
        """)
        
        # Execute the query
        result = db.session.execute(query, {'username': username}).fetchone()
        
        if result:
            user_id, db_username, password_hash, email, account_data = result
            
            if not password_hash:
                logger.warning(f"No password found for user: {username}")
                return None
                
            try:
                # Verify the password
                if check_password_hash(password_hash, password):
                    logger.info(f"Authentication successful for user: {db_username}")
                    
                    # Parse account_data if it's a string
                    if isinstance(account_data, str):
                        try:
                            account_data = json.loads(account_data)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse account_data for user: {username}")
                            account_data = {}
                    
                    # Check if email verification is required
                    if current_app.config.get('ENABLE_EMAIL_VERIFICATION', True):
                        email_verified = account_data.get('email_verified', False) if account_data else False
                        if not email_verified:
                            logger.warning(f"Email not verified for user: {username}")
                            return None
                    
                    # Create and return user object
                    user = User(
                        id=user_id,
                        username=db_username,
                        password=password_hash,
                        email=email,
                        user_data=account_data if account_data else {}
                    )
                    return user
                else:
                    logger.warning(f"Invalid password for user: {username}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error during authentication: {str(e)}")
                logger.debug(f"Stack trace:\n{traceback.format_exc()}")
                return None
                
        else:
            logger.warning(f"No user found with username/email: {username}")
            return None
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        return None

def generate_verification_token(email):
    """Generate a secure token for email verification."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-verification')

def confirm_verification_token(token, expiration=86400):
    """Verify the token and return the email if valid."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt='email-verification',
            max_age=expiration
        )
        return email
    except:
        return None

def send_verification_email(user_email, username):
    """Send a verification email to the user with a verification link."""
    try:
        from . import mail
        from flask_mail import Message
        
        token = generate_verification_token(user_email)
        verify_url = url_for('auth.verify_email', token=token, _external=True)
        
        msg = Message(
            'Verify Your Email',
            recipients=[user_email],
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        msg.body = f'''Welcome {username}!

Please click the following link to verify your email:
{verify_url}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.
'''
        
        mail.send(msg)
        logger.info(f"Verification email sent to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user_email}: {str(e)}")
        return False
