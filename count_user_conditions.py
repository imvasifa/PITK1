from postgres_db import db

def count_user_conditions(username):
    """Count the number of conditions for a given username"""
    try:
        cur = db.get_cursor()
        cur.execute("""
            SELECT user_data->'conditions' as conditions 
            FROM users 
            WHERE user_data->'account'->>'username' = %s
        """, (username,))
        
        result = cur.fetchone()
        if not result or 'conditions' not in result or not result['conditions']:
            return 0
            
        conditions = result['conditions']
        return len(conditions) if isinstance(conditions, list) else 0
        
    except Exception as e:
        print(f"❌ Error counting conditions: {e}")
        return -1

if __name__ == "__main__":
    username = "indianplans"  # Default username to check
    count = count_user_conditions(username)
    if count >= 0:
        print(f"User '{username}' has {count} conditions")
    else:
        print(f"Could not retrieve conditions for user '{username}'")
