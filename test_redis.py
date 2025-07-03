import os
import redis
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_redis_connection():
    """Test Redis connection with the provided credentials"""
    try:
        # Get Redis URL from environment or use the one provided
        redis_url = os.getenv('REDIS_URL')
        
        if not redis_url:
            logger.error("REDIS_URL not found in environment variables")
            return False
            
        logger.info(f"Connecting to Redis at: {redis_url.split('@')[-1]}")
        
        # Create Redis client
        redis_client = redis.Redis.from_url(
            redis_url,
            ssl_cert_reqs="none",  # Disable SSL certificate verification
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True
        )
        
        # Test connection
        if redis_client.ping():
            logger.info("✅ Successfully connected to Redis")
            
            # Test setting and getting a key
            test_key = "test:connection"
            test_value = "success"
            
            redis_client.set(test_key, test_value, ex=60)  # Set with 60s expiration
            retrieved_value = redis_client.get(test_key)
            
            if retrieved_value == test_value:
                logger.info("✅ Successfully set and retrieved test key")
            else:
                logger.warning(f"Test key value mismatch: expected '{test_value}', got '{retrieved_value}'")
                
            # List all keys for debugging
            try:
                all_keys = redis_client.keys('*')
                logger.info(f"\nCurrent Redis keys ({len(all_keys)} total):")
                for key in all_keys[:10]:  # Show first 10 keys
                    key_type = redis_client.type(key)
                    ttl = redis_client.ttl(key)
                    logger.info(f"  {key} (type: {key_type}, ttl: {ttl if ttl != -1 else 'no expiry'}")
                if len(all_keys) > 10:
                    logger.info(f"  ... and {len(all_keys) - 10} more keys")
            except Exception as e:
                logger.warning(f"Could not list all keys: {str(e)}")
                
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {str(e)}")
        return False

if __name__ == "__main__":
    test_redis_connection()
