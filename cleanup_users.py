from postgres_db import db

def list_users():
    """List all users in the database"""
    try:
        cur = db.get_cursor()
        cur.execute("""
            SELECT id, user_data->'account'->>'username' as username
            FROM users
            ORDER BY id
        """)
        users = cur.fetchall()
        print("\n=== Current Users ===")
        for user in users:
            print(f"ID: {user['id']}, Username: {user['username']}")
        return users
    except Exception as e:
        print(f"❌ Error listing users: {e}")
        return []

def delete_users_except_first_three():
    """Delete all users except the first 3 IDs"""
    try:
        # First, list all users
        users = list_users()
        if not users:
            return
            
        # Get the first 3 user IDs
        keep_ids = [str(user['id']) for user in users[:3]]
        
        print(f"\n⚠️  This will delete all users except IDs: {', '.join(keep_ids)}")
        confirm = input("Are you sure you want to continue? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ Operation cancelled")
            return
            
        # Delete users not in the first 3 IDs
        cur = db.get_cursor()
        cur.execute("""
            DELETE FROM users 
            WHERE id NOT IN %s
            RETURNING id, user_data->'account'->>'username' as username
        """, (tuple(keep_ids),))
        
        deleted_users = cur.fetchall()
        db.conn.commit()
        
        print(f"\n✅ Deleted {len(deleted_users)} users:")
        for user in deleted_users:
            print(f"- ID: {user['id']}, Username: {user['username']}")
            
    except Exception as e:
        print(f"❌ Error deleting users: {e}")
        if 'db' in locals() and hasattr(db, 'conn'):
            db.conn.rollback()

if __name__ == "__main__":
    print("=== User Cleanup Tool ===")
    delete_users_except_first_three()
    print("\n=== Remaining Users ===")
    list_users()
