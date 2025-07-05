"""
This module contains the data models for the application.
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import logging

logger = logging.getLogger(__name__)

class User(UserMixin):
    """User model for authentication and user-related operations."""
    
    def __init__(self, id=None, username='', password='', email='', user_data=None):
        """Initialize a User instance.
        
        Args:
            id: The user's unique identifier
            username: The user's username
            password: The user's hashed password
            email: The user's email address
            user_data: Additional user data as a dictionary
        """
        try:
            self.id = int(id) if id is not None and str(id).strip() not in ['', 'id'] else None
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Invalid ID format: {id} (type: {type(id)}) - Using None")
            self.id = None
        
        self.username = username
        self._password = password
        self.email = email
        self._user_data = user_data or {}
        
        # Set default values if not provided
        if not self.username and 'username' in self._user_data.get('account', {}):
            self.username = self._user_data['account']['username']
        
        if not self.email and 'email' in self._user_data.get('account', {}).get('profile', {}):
            self.email = self._user_data['account']['profile']['email']
        
        logger.debug(f"Created User - ID: {self.id}, Username: {self.username}")
    
    @property
    def password(self):
        """Prevent password from being accessed."""
        return self._password
    
    @password.setter
    def password(self, password):
        """Set password to a hashed password."""
        self._password = generate_password_hash(password)
    
    def verify_password(self, password):
        """Check if hashed password matches actual password."""
        return check_password_hash(self._password, password)
    
    @property
    def is_active(self):
        """Check if user is active."""
        return self._user_data.get('account', {}).get('is_active', True)
    
    @property
    def is_authenticated(self):
        """Check if user is authenticated."""
        return self.id is not None
    
    @property
    def is_anonymous(self):
        """Check if user is anonymous."""
        return self.id is None
    
    def get_id(self):
        """Return the user ID as a string."""
        return str(self.id) if self.id else None
    
    def to_dict(self):
        """Convert user object to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'user_data': self._user_data
        }
    
    @classmethod
    def from_dict(cls, user_dict):
        """Create a User instance from a dictionary."""
        return cls(
            id=user_dict.get('id'),
            username=user_dict.get('username', ''),
            password=user_dict.get('password', ''),
            email=user_dict.get('email', ''),
            user_data=user_dict.get('user_data', {})
        )
    
    def __repr__(self):
        return f"<User {self.username}>"


class UserProfile:
    """User profile model for additional user information."""
    
    def __init__(self, user_id, **kwargs):
        """Initialize a UserProfile instance.
        
        Args:
            user_id: The ID of the user this profile belongs to
            **kwargs: Additional profile attributes
        """
        self.user_id = user_id
        self.full_name = kwargs.get('full_name', '')
        self.bio = kwargs.get('bio', '')
        self.phone = kwargs.get('phone', '')
        self.address = kwargs.get('address', '')
        self.profile_image = kwargs.get('profile_image', '')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
    
    def to_dict(self):
        """Convert profile to dictionary."""
        return {
            'user_id': self.user_id,
            'full_name': self.full_name,
            'bio': self.bio,
            'phone': self.phone,
            'address': self.address,
            'profile_image': self.profile_image,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a UserProfile instance from a dictionary."""
        return cls(
            user_id=data.get('user_id'),
            full_name=data.get('full_name', ''),
            bio=data.get('bio', ''),
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            profile_image=data.get('profile_image', ''),
            created_at=data.get('created_at', datetime.utcnow()),
            updated_at=data.get('updated_at', datetime.utcnow())
        )


class UserCondition:
    """Model for user conditions."""
    
    def __init__(self, user_id, condition_id, name, scan_clause, **kwargs):
        """Initialize a UserCondition instance.
        
        Args:
            user_id: The ID of the user this condition belongs to
            condition_id: The unique identifier for this condition
            name: The name of the condition
            scan_clause: The scan clause associated with the condition
            **kwargs: Additional condition attributes
        """
        self.id = condition_id
        self.user_id = user_id
        self.name = name
        self.scan_clause = scan_clause
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.metadata = kwargs.get('metadata', {})
    
    def to_dict(self):
        """Convert condition to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'scan_clause': self.scan_clause,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a UserCondition instance from a dictionary."""
        return cls(
            user_id=data.get('user_id'),
            condition_id=data.get('id'),
            name=data.get('name', ''),
            scan_clause=data.get('scan_clause', ''),
            created_at=data.get('created_at', datetime.utcnow()),
            updated_at=data.get('updated_at', datetime.utcnow()),
            metadata=data.get('metadata', {})
        )
