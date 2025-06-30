import psycopg2
from psycopg2 import sql
import json
import sys
from app3 import db, app  # Import both db and app from app3

def update_all_users_premium():
    try:
        print("Connecting to the database...")
        conn = db.conn  # Use the existing database connection from your Flask app
        cur = conn.cursor()
        
        # First, check how many users we have
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        print(f"Found {total_users} users in the database")
        
        # Update all users to premium = "no"
        update_query = """
        UPDATE users
        SET user_data = jsonb_set(
            COALESCE(user_data, '{}'::jsonb),
            '{account,profile,premium}',
            '"no"',
            true
        )
        WHERE user_data->'account'->'profile'->>'premium' IS DISTINCT FROM 'no'
           OR user_data->'account'->'profile'->>'premium' IS NULL
        RETURNING id
        """
        
        print("Updating users...")
        cur.execute(update_query)
        updated_count = cur.rowcount
        conn.commit()
        
        # Verify the update
        cur.execute("""
        SELECT COUNT(*) 
        FROM users
        WHERE user_data->'account'->'profile'->>'premium' = 'no'
        """)
        verified_count = cur.fetchone()[0]
        
        print("\nUpdate Summary:")
        print(f"Total users in database: {total_users}")
        print(f"Users updated to premium='no': {updated_count}")
        print(f"Verified users with premium='no': {verified_count}")
        
        if verified_count == total_users:
            print("\n✅ Success! All users now have premium='no'")
        else:
            print(f"\n⚠️ Warning: {total_users - verified_count} users might not have been updated correctly")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        # Don't close the connection as it's managed by Flask

if __name__ == "__main__":
    print("=== Set All Users Premium to 'no' ===")
    with app.app_context():  # Create application context
        update_all_users_premium()
    input("\nPress Enter to exit...")