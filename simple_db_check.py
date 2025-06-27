from postgres_db import db

def check_database():
    print("=== Simple Database Check ===")
    
    try:
        # Get cursor
        cur = db.get_cursor()
        print("✅ Successfully got database cursor")
        
        # Check if users table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        """)
        users_table_exists = cur.fetchone()['exists']
        
        if not users_table_exists:
            print("❌ Users table does not exist in the database")
            return
            
        print("✅ Users table exists")
        
        # Get user count
        cur.execute("SELECT COUNT(*) as count FROM users")
        count = cur.fetchone()['count']
        print(f"✅ Found {count} users in the database")
        
        if count > 0:
            # Get first few users
            cur.execute("""
                SELECT id, 
                       user_data->'account'->>'username' as username,
                       user_data->'account'->>'email' as email
                FROM users 
                LIMIT 5
            """)
            
            users = cur.fetchall()
            print("\n=== Sample Users ===")
            for user in users:
                print(f"ID: {user['id']}")
                print(f"Username: {user['username']}")
                print(f"Email: {user['email']}")
                print("-" * 30)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
    input("\nPress Enter to exit...")
