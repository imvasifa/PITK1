"""
This module contains email-related utility functions.
"""
from flask import current_app, url_for, render_template
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def send_email(subject, sender, recipients, text_body, html_body=None, attachments=None):
    """Send an email.
    
    Args:
        subject: Email subject
        sender: Email sender
        recipients: List of recipient email addresses
        text_body: Plain text body of the email
        html_body: HTML body of the email (optional)
        attachments: List of attachments (optional)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        msg = Message(
            subject=subject,
            sender=sender,
            recipients=recipients
        )
        
        msg.body = text_body
        if html_body:
            msg.html = html_body
        
        if attachments:
            for attachment in attachments:
                msg.attach(*attachment)
        
        mail = current_app.extensions.get('mail')
        if not mail:
            logger.error("Mail extension not initialized")
            return False
            
        mail.send(msg)
        logger.info(f"Email sent to {', '.join(recipients)} with subject: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_verification_email(user_email, username):
    """Send an email verification link to the user.
    
    Args:
        user_email: The user's email address
        username: The user's username
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Generate verification token
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        token = serializer.dumps(user_email, salt='email-verification')
        
        # Create verification URL
        verify_url = url_for('auth.verify_email', token=token, _external=True)
        
        # Render email templates
        subject = "Verify Your Email Address"
        
        # Text version
        text_body = f"""
        Welcome {username}!
        
        Thank you for registering. Please click the following link to verify your email address:
        
        {verify_url}
        
        This link will expire in 24 hours.
        
        If you did not create an account, please ignore this email.
        """
        
        # HTML version
        html_body = render_template(
            'emails/verify_email.html',
            username=username,
            verify_url=verify_url
        )
        
        # Send email
        return send_email(
            subject=subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user_email],
            text_body=text_body,
            html_body=html_body
        )
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {user_email}: {str(e)}")
        return False

def send_password_reset_email(user_email, username):
    """Send a password reset email to the user.
    
    Args:
        user_email: The user's email address
        username: The user's username
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Generate password reset token
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        token = serializer.dumps(user_email, salt='password-reset')
        
        # Create reset URL
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        # Render email templates
        subject = "Reset Your Password"
        
        # Text version
        text_body = f"""
        Hello {username},
        
        You recently requested to reset your password. Click the link below to reset it:
        
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you did not request a password reset, please ignore this email.
        """
        
        # HTML version
        html_body = render_template(
            'emails/reset_password.html',
            username=username,
            reset_url=reset_url
        )
        
        # Send email
        return send_email(
            subject=subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user_email],
            text_body=text_body,
            html_body=html_body
        )
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")
        return False

def generate_email_token(email, salt, expiration=3600):
    """Generate a secure token for email-related operations.
    
    Args:
        email: The email address to generate a token for
        salt: The salt to use for the token
        expiration: Token expiration time in seconds (default: 1 hour)
    
    Returns:
        str: The generated token
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=salt)

def verify_email_token(token, salt, max_age=3600):
    """Verify an email token and return the email if valid.
    
    Args:
        token: The token to verify
        salt: The salt used to generate the token
        max_age: Maximum age of the token in seconds (default: 1 hour)
    
    Returns:
        str: The email address if the token is valid, None otherwise
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=salt,
            max_age=max_age
        )
        return email
    except:
        return None
