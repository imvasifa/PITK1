import redis
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Using the exact same configuration as redis_set_key.py
    REDIS_URL = "rediss://red-d109u7qli9vc73dkjp30:gjyOjstc7DXWndtoFx5X8Qz7vGbia5RW@ohio-keyvalue.render.com:6379"
    
    # Parse the Redis URL
    url_parts = redis.connection.parse_url(REDIS_URL)
    
    # Connect to Redis
    r = redis.Redis(
        host=url_parts['host'],
        port=url_parts['port'],
        username=url_parts['username'],
        password=url_parts['password'],
        ssl=True,
        ssl_cert_reqs=None,
        ssl_check_hostname=False,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    
    # Test connection
    if r.ping():
        print("✅ Successfully connected to Redis")
        
        # Test setting and getting a key
        test_key = "test:connection"
        r.set(test_key, "test_value")
        value = r.get(test_key)
        print(f"Test key value: {value}")
        
        # List all keys
        print("\nCurrent Redis keys:")
        for key in r.keys('*'):
            print(f"  {key}")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
