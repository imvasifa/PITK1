import sys
import json
from postgres_db import db

def check_users():
    print("Checking users in the database...")
    try:
        cur = db.get_cursor()
        
        # Check if users table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            print("❌ Users table does not exist in the database.")
            return
            
        # Get count of users
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        print(f"✅ Found {count} users in the database")
        
        # Get first 5 users
        cur.execute("""
            SELECT id, 
                   user_data->'account'->>'username' as username,
                   user_data->'account'->>'email' as email,
                   created_at
            FROM users 
            LIMIT 5
        """)
        
        columns = [desc[0] for desc in cur.description]
        users = cur.fetchall()
        
        if not users:
            print("\nNo users found in the database.")
            return
            
        print("\n=== First few users in database ===")
        for user in users:
            user_dict = dict(zip(columns, user))
            print(json.dumps(user_dict, indent=2, default=str))
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Error checking users: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_users()
    input("\nPress Enter to exit...")
