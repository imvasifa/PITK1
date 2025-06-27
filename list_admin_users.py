from postgres_db import db

def list_admin_users():
    try:
        # Get cursor from the database connection
        cur = db.get_cursor()
        
        # Query to get admin users (IDs 1, 2, 3)
        cur.execute("""
            SELECT id, 
                   user_data->'account'->>'username' as username, 
                   user_data->'account'->>'email' as email
            FROM users 
            WHERE id IN (1, 2, 3)
            ORDER BY id
        """)
        
        admin_users = cur.fetchall()
        
        if not admin_users:
            print("No admin users found in the database.")
            return
            
        print("\nAdmin Users (ID, Username, Email):")
        print("=" * 50)
        for user in admin_users:
            print(f"ID: {user['id']}, Username: {user['username']}, Email: {user['email']}")
        print("=" * 50 + "\n")
            
    except Exception as e:
        print(f"❌ Error fetching admin users: {e}")

if __name__ == "__main__":
    list_admin_users()
