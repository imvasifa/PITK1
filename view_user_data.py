from postgres_db import db

def get_complete_user_data(user_id):
    """
    Fetch complete user data including all fields from the database
    """
    try:
        # Get database cursor
        cur = db.get_cursor()
        if not cur:
            print("❌ Failed to get database cursor")
            return None
            
        # Get all user data including the JSONB field
        cur.execute("""
            SELECT * 
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user_data = cur.fetchone()
        
        if not user_data:
            print(f"❌ No user found with ID: {user_id}")
            return None
            
        # Convert to dict for better display
        columns = [desc[0] for desc in cur.description]
        user_dict = dict(zip(columns, user_data))
        
        print("\n=== Complete User Data ===")
        for key, value in user_dict.items():
            if key == 'user_data' and value and isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")
                
        return user_dict
        
    except Exception as e:
        print(f"❌ Error fetching user data: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Get user ID from input (default to 1 for admin)
    user_id = input("Enter user ID to view (default: 1): ").strip()
    user_id = int(user_id) if user_id.isdigit() else 1
    
    print(f"\nFetching data for user ID: {user_id}")
    get_complete_user_data(user_id)
    
    input("\nPress Enter to exit...")
