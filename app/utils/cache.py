"""
This module provides caching utilities using Redis.
"""
import pickle
import json
import logging
from functools import wraps
from datetime import timedelta
from flask import current_app

logger = logging.getLogger(__name__)

# Cache instance that will be initialized in the app factory
cache = None

def init_cache(app):
    """Initialize the cache with the given Flask application.
    
    Args:
        app: The Flask application instance
    """
    global cache
    
    try:
        from redis import Redis
        from redis.exceptions import RedisError
        
        # Get Redis configuration from app config
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        
        # Initialize Redis connection
        cache = Redis.from_url(
            redis_url,
            decode_responses=False,  # We'll handle serialization ourselves
            socket_timeout=5,        # 5 seconds timeout for operations
            socket_connect_timeout=5,# 5 seconds timeout for connection
            retry_on_timeout=True,   # Retry on timeout
            max_connections=20       # Maximum number of connections in the pool
        )
        
        # Test the connection
        cache.ping()
        
        app.logger.info(f"Cache initialized with Redis at {redis_url}")
        
    except Exception as e:
        app.logger.error(f"Failed to initialize cache: {str(e)}")
        # Fall back to a simple in-memory cache if Redis is not available
        cache = SimpleCache()
        app.logger.warning("Falling back to in-memory cache")


def get_cached_data(key, default=None, ttl=None):
    """Get data from the cache.
    
    Args:
        key: The cache key
        default: Default value to return if key is not found
        ttl: Time to live in seconds (only used if default is provided and key is not found)
    
    Returns:
        The cached data or default value if not found
    """
    if cache is None:
        return default
    
    try:
        value = cache.get(key)
        if value is not None:
            try:
                return pickle.loads(value)
            except (pickle.PickleError, TypeError):
                try:
                    return json.loads(value.decode('utf-8'))
                except (ValueError, UnicodeDecodeError):
                    return value.decode('utf-8')
        
        # If we have a default value and ttl, set it in the cache
        if default is not None and ttl is not None:
            set_cached_data(key, default, ttl)
            
        return default
        
    except Exception as e:
        logger.error(f"Error getting cached data for key {key}: {str(e)}")
        return default


def set_cached_data(key, value, ttl=None):
    """Set data in the cache.
    
    Args:
        key: The cache key
        value: The value to cache
        ttl: Time to live in seconds (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if cache is None:
        return False
    
    try:
        # Try to pickle the value first
        try:
            serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        except (pickle.PickleError, TypeError):
            # Fall back to JSON if pickle fails
            try:
                serialized = json.dumps(value).encode('utf-8')
            except (TypeError, ValueError):
                # Fall back to string representation
                serialized = str(value).encode('utf-8')
        
        if ttl is not None:
            cache.setex(key, timedelta(seconds=ttl), serialized)
        else:
            cache.set(key, serialized)
            
        return True
        
    except Exception as e:
        logger.error(f"Error setting cached data for key {key}: {str(e)}")
        return False


def delete_cached_data(key):
    """Delete data from the cache.
    
    Args:
        key: The cache key or pattern to delete
    
    Returns:
        int: Number of keys deleted
    """
    if cache is None:
        return 0
    
    try:
        # If the key contains a wildcard, use scan to find matching keys
        if '*' in key or '?' in key or '[' in key:
            keys = []
            cursor = '0'
            
            while cursor != 0:
                cursor, partial_keys = cache.scan(
                    cursor=cursor,
                    match=key,
                    count=1000  # Process 1000 keys at a time
                )
                keys.extend(partial_keys)
                
            if not keys:
                return 0
                
            return cache.delete(*keys)
        else:
            return cache.delete(key)
            
    except Exception as e:
        logger.error(f"Error deleting cached data for key {key}: {str(e)}")
        return 0


def cached(timeout=300, key_prefix='view/%s', unless=None):
    """Decorator to cache the result of a function.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Cache key prefix (use %s for function name)
        unless: Callable that returns True to bypass caching
    
    Returns:
        Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip caching if specified
            if callable(unless) and unless() is True:
                return f(*args, **kwargs)
            
            # Generate cache key
            cache_key = key_prefix % f.__name__
            
            # Try to get cached result
            result = get_cached_data(cache_key)
            
            if result is None:
                # Call the original function
                result = f(*args, **kwargs)
                
                # Cache the result
                set_cached_data(cache_key, result, timeout)
            
            return result
        return decorated_function
    return decorator


class SimpleCache(dict):
    """Simple in-memory cache implementation."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expiry_times = {}
    
    def get(self, key, default=None):
        """Get a value from the cache."""
        if key in self and (key not in self._expiry_times or self._expiry_times[key] > datetime.now()):
            return super().get(key, default)
        
        if key in self._expiry_times:
            del self._expiry_times[key]
            if key in self:
                del self[key]
                
        return default
    
    def set(self, key, value, ex=None):
        """Set a value in the cache."""
        self[key] = value
        if ex is not None:
            self._expiry_times[key] = datetime.now() + timedelta(seconds=ex)
        return True
    
    def setex(self, key, time, value):
        """Set a value in the cache with an expiration time."""
        return self.set(key, value, ex=time.total_seconds() if hasattr(time, 'total_seconds') else time)
    
    def delete(self, *keys):
        """Delete one or more keys from the cache."""
        count = 0
        for key in keys:
            if key in self:
                del self[key]
                count += 1
            if key in self._expiry_times:
                del self._expiry_times[key]
        return count
    
    def scan(self, cursor=0, match=None, count=None, _type=None):
        """Scan for keys in the cache."""
        # This is a simplified implementation that doesn't support all Redis features
        keys = list(self.keys())
        
        if match:
            import fnmatch
            keys = [k for k in keys if fnmatch.fnmatch(k, match)]
        
        # Simple pagination
        if count is not None and count < len(keys):
            keys = keys[:count]
        
        return 0, keys  # Return cursor=0 to indicate completion
