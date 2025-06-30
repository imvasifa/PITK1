import redis
import os
import random
import string
import ssl

# Redis connection details from redis.txt
REDIS_URL = "rediss://red-d109u7qli9vc73dkjp30:gjyOjstc7DXWndtoFx5X8Qz7vGbia5RW@ohio-keyvalue.render.com:6379"

# Parse the Redis URL
url_parts = redis.connection.parse_url(REDIS_URL)

# Create SSL context for secure connection
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def generate_licence_key(length=16):
    """Generate a random alphanumeric key of specified length."""
    characters = string.ascii_uppercase + string.digits  # A-Z and 0-9
    return ''.join(random.choice(characters) for _ in range(length))

try:
    # Connect to Redis with SSL
    r = redis.Redis(
        host=url_parts['host'],
        port=url_parts['port'],
        username=url_parts['username'],
        password=url_parts['password'],
        ssl=True,
        ssl_cert_reqs=None,
        ssl_ca_certs=None,
        ssl_certfile=None,
        ssl_keyfile=None,
        ssl_check_hostname=False,
        decode_responses=True  # Automatically decode responses to strings
    )
    
    # Generate a new 16-character alphanumeric licence key (uppercase)
    licence_key = generate_licence_key(16)
    
    # Store the licence key as an individual key (no TTL)
    # Using the format licence:key:{actual_key}
    redis_key = f'licence:key:{licence_key}'
    
    # Check if key already exists
    if r.exists(redis_key):
        print(f"⚠️  Key {licence_key} already exists in Redis")
    else:
        r.set(redis_key, 'active')
        print(f"✅ Created new licence key: {licence_key}")
    
    # Get the TTL for this specific key
    ttl = r.ttl(redis_key)
    
    print(f"Generated Licence Key: {licence_key}")
    print(f"Stored in Redis with TTL: {ttl} seconds ({(ttl//60)} minutes and {ttl%60} seconds)")
    
    # Print all active keys
    print("\n--- Active Licence Keys ---")
    print(f"Key created: {licence_key} (Expires in: {ttl} seconds)")
    
    # List all active keys
    all_keys = r.keys('licence:key:*')
    if all_keys:
        print("\nAll active keys:")
        for key in all_keys:
            key_ttl = r.ttl(key)
            key_name = key.replace('licence:key:', '')
            print(f"- {key_name} (Expires in: {key_ttl} seconds)")
    else:
        print("No active keys found")
    
except Exception as e:
    print(f"An error occurred: {str(e)}")
    
finally:
    # Clean up the connection
    if 'r' in locals():
        r.close()
