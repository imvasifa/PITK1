from postgres_db import db
import json

def view_raw_user_data(username=None):
    if username is None:
        username = input("Enter username [indianplans]: ").strip() or "indianplans"
    try:
        # Get raw user data
        cur = db.get_cursor()
        cur.execute("""
            SELECT id, user_data 
            FROM pitk3 
            WHERE user_data->'account'->>'username' = %s
        """, (username,))
        
        user = cur.fetchone()
        
        if not user:
            print(f"No user found with username: {username}")
            return
            
        print(f"\n=== RAW PITK3 DATA FOR: {username} ===\n")
        print(f"User ID: {user['id']}")
        print("\nComplete user_data JSON:")
        print(json.dumps(user['user_data'], indent=2, default=str))
        
        # Show conditions separately
        if 'conditions' in user['user_data']:
            conditions = user['user_data']['conditions']
            print(f"\n=== {len(conditions)} CONDITIONS ===")
            for i, condition in enumerate(conditions, 1):
                print(f"\nCONDITION {i}:")
                print(json.dumps(condition, indent=2, default=str))
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    view_raw_user_data()
