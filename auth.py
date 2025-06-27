from werkzeug.security import check_password_hash
from models import User, get_user_by_username, update_user_password
from flask_login import login_user
import logging

logger = logging.getLogger(__name__)

def authenticate_user(username, password):
    """
    Authenticate a user with the given username and password.
    
    Args:
        username: The username to authenticate
        password: The password to verify
        
    Returns:
        User object if authentication succeeds, None otherwise
    """
    logger.info(f"Attempting to authenticate user: {username}")
    
    try:
        # Get user from database
        user = User.get_by_username(username)
        if not user:
            logger.error(f"User not found: {username}")
            return None
        
        # Check if we have a valid password hash
        if not user.password:
            logger.error(f"No password hash found for user: {username}")
            return None
            
        # Check password (supports bcrypt and plain text migration)
        if check_password_hash(user.password, password) or user.password == password:
            logger.info(f"Authentication successful for user: {username}")
            return user
            
        logger.error(f"Invalid password for user: {username}")
        return None
        
    except Exception as e:
        logger.error(f"Error during authentication for {username}: {e}", exc_info=True)
        return None
