from postgres_db import db
import json

def get_admin_conditions():
    """Get the list of admin conditions from app3.py"""
    print("\n=== Admin Conditions ===")
    try:
        # These would be imported from app3.py in a real scenario
        from app3 import admin_conditions
        print(f"Found {len(admin_conditions)} admin conditions")
        for i, cond in enumerate(admin_conditions[:5], 1):  # Show first 5
            print(f"{i}. {cond.get('name', 'Unnamed')} - {cond.get('type', 'No type')}")
        if len(admin_conditions) > 5:
            print(f"... and {len(admin_conditions) - 5} more")
        return admin_conditions
    except Exception as e:
        print(f"❌ Error getting admin conditions: {e}")
        return []

def get_user_conditions(user_id):
    """Get conditions for a specific user from the database"""
    print(f"\n=== User {user_id} Conditions ===")
    try:
        cur = db.get_cursor()
        cur.execute("""
            SELECT user_data->'conditions' as conditions
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        result = cur.fetchone()
        
        if not result or 'conditions' not in result or not result['conditions']:
            print("No conditions found for this user")
            return []
            
        conditions = result['conditions']
        print(f"Found {len(conditions)} conditions for user {user_id}")
        for i, cond in enumerate(conditions[:5], 1):  # Show first 5
            print(f"{i}. {cond.get('name', 'Unnamed')} - {cond.get('type', 'No type')}")
        if len(conditions) > 5:
            print(f"... and {len(conditions) - 5} more")
            
        return conditions
        
    except Exception as e:
        print(f"❌ Error getting user conditions: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # Get admin conditions
    admin_conditions = get_admin_conditions()
    
    # Get conditions for user 1 (rahim)
    get_user_conditions(1)
    
    input("\nPress Enter to exit...")
