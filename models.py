from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from postgres_db import db
import json
import logging

logger = logging.getLogger(__name__)

class User(UserMixin):
    def __init__(self, id, username, password=None, email=''):
        # Validate and normalize the user ID
        if not id or str(id).strip().lower() in ('none', 'null', 'id', ''):
            raise ValueError("Invalid user ID")

        self.id = str(id).strip()  # Flask-Login expects .id to be a string
        self.username = username
        self.password = password
        self.email = email
        
    def get_id(self):
        return self.id
        
    @classmethod
    def get(cls, user_id):
        """Get user by ID"""
        user_data = get_user_by_id(user_id)
        if not user_data:
            return None
        return cls(
            id=user_data[0],
            username=user_data[1],
            email=user_data[3] if len(user_data) > 3 else ''
        )
    
    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        user_data = get_user_by_username(username)
        if not user_data:
            return None
        return cls(
            id=user_data[0],
            username=user_data[1],
            password=user_data[2],
            email=user_data[3] if len(user_data) > 3 else ''
        )

def get_user_by_username(username):
    """
    Get a user by username from the database.
    
    Args:
        username: The username to look up
        
    Returns:
        tuple: (user_id, username, password_hash, user_data) or None if not found
    """
    try:
        cur = db.get_cursor()
        if not cur:
            logger.error("Failed to get database cursor")
            return None
            
        query = """
            SELECT id, username, 
                   user_data->'account'->>'password' as password_hash,
                   user_data
            FROM users 
            WHERE username = %s
            LIMIT 1
        """
        
        cur.execute(query, (username,))
        return cur.fetchone()
        
    except Exception as e:
        logger.error(f"Error getting user by username {username}: {e}", exc_info=True)
        return None

def update_user_password(user_id, new_password_hash):
    """
    Update a user's password in the database.
    
    Args:
        user_id: The ID of the user
        new_password_hash: The new password hash
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        cur = db.get_cursor()
        if not cur:
            logger.error("Failed to get database cursor")
            return False
            
        query = """
            UPDATE users 
            SET user_data = jsonb_set(
                COALESCE(user_data, '{}'::jsonb),
                '{account,password}'::text[],
                to_jsonb(%s::text),
                true
            )
            WHERE id = %s
        """
        
        cur.execute(query, (new_password_hash, user_id))
        db.conn.commit()
        return cur.rowcount > 0
        
    except Exception as e:
        logger.error(f"Error updating password for user {user_id}: {e}", exc_info=True)
        if db.conn:
            db.conn.rollback()
        return False
