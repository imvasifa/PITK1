from postgres_db import db
import json

def view_user_conditions(user_id=1):
    """View conditions for a specific user"""
    try:
        print(f"\n=== Viewing conditions for user ID: {user_id} ===")
        
        # Get database cursor
        cur = db.get_cursor()
        if not cur:
            print("❌ Failed to get database cursor")
            return
            
        # Get user data with conditions
        cur.execute("""
            SELECT user_data->'conditions' as conditions
            FROM pitk3 
            WHERE id = %s
        """, (user_id,))
        
        result = cur.fetchone()
        
        if not result or 'conditions' not in result:
            print("❌ No user data found or conditions field is missing")
            return
            
        conditions = result['conditions']
        
        if not conditions:
            print("ℹ️ No conditions found for this user")
            return
            
        print(f"Found {len(conditions)} conditions:")
        print("-" * 50)
        
        for i, condition in enumerate(conditions, 1):
            print(f"{i}. Name: {condition.get('name', 'Unnamed')}")
            print(f"   Type: {condition.get('type', 'No type')}")
            if 'link' in condition:
                print(f"   Link: {condition['link']}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Get user ID from input (default to 1 for admin)
    user_id = input("Enter user ID to view conditions (default: 1): ").strip()
    user_id = int(user_id) if user_id.isdigit() else 1
    
    view_user_conditions(user_id)
    input("\nPress Enter to exit...")
