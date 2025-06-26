import json
import os
import tempfile
import logging
from pathlib import Path
import portalocker
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self, data_dir: str = '.', filename: str = 'users.json'):
        """
        Initialize the UserManager with the path to the users.json file.
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.data_dir / filename
        self.lock_file = str(self.filepath) + '.lock'
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Ensure the users.json file exists with proper structure."""
        if not self.filepath.exists():
            with open(self.filepath, 'w') as f:
                json.dump({}, f)
    
    def _get_canonical_user_key(self, user_id: str) -> str:
        """Convert any user ID to the canonical format (user_X)."""
        user_id = str(user_id)
        if user_id.startswith('user_'):
            return user_id
        return f'user_{user_id}'
    
    def _load_data(self) -> Dict[str, Any]:
        """Load and return the entire users data with file locking."""
        if not self.filepath.exists():
            return {}
            
        with portalocker.Lock(self.lock_file, timeout=5):
            with open(self.filepath, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    logger.error(f"Error decoding {self.filepath}")
                    return {}
    
    def _save_data(self, data: Dict[str, Any]) -> bool:
        """Save data to file with atomic write and file locking."""
        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir, prefix='.users_')
        
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            with portalocker.Lock(self.lock_file, timeout=5):
                os.replace(temp_path, self.filepath)
                return True
                
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            return False
    
    def get_user_conditions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conditions for a user."""
        user_key = self._get_canonical_user_key(user_id)
        data = self._load_data()
        
        user_data = data.get(user_key, {})
        account = user_data.get('account', {})
        return account.get('conditions', [])
    
    def save_user_conditions(self, user_id: str, conditions: List[Dict[str, Any]]) -> bool:
        """Save conditions for a user."""
        user_key = self._get_canonical_user_key(user_id)
        data = self._load_data()
        
        # Get or create user data
        user_data = data.setdefault(user_key, {})
        
        # Get or create account data
        account = user_data.setdefault('account', {})
        
        # Update conditions
        account['conditions'] = conditions
        
        # Ensure required fields exist
        if 'username' not in account:
            account['username'] = str(user_id)
        if 'password' not in account:
            account['password'] = ''
        if 'profile' not in account:
            account['profile'] = {}
        
        # Save the data
        return self._save_data(data)

# Singleton instance
user_manager = UserManager()
