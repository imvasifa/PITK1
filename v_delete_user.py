import sys
import os
import json
from app3 import db  # Import the database connection from your app

def list_users():
    """List all users from the PITK3 table"""
    try:
        cur = db.get_cursor()
        cur.execute("""
            SELECT id, user_data->'account'->>'username' as username
            FROM PITK3
            ORDER BY id
        """)
        users = cur.fetchall()
        
        if not users:
            print("No users found in the database.")
            return []
            
        print("\n=== List of Users ===")
        print("ID  | Username")
        print("-" * 30)
        for user in users:
            print(f"{user['id']:3} | {user['username']}")
        print()
        return users
        
    except Exception as e:
        print(f"Error listing users: {e}")
        return []

def delete_user(user_id):
    """Delete a user by ID"""
    try:
        # First, get username for confirmation
        cur = db.get_cursor()
        cur.execute("""
            SELECT user_data->'account'->>'username' as username
            FROM PITK3 
            WHERE id = %s
        """, (user_id,))
        
        result = cur.fetchone()
        if not result:
            print(f"Error: No user found with ID {user_id}")
            return False
            
        username = result['username']
        
        # Ask for confirmation
        confirm = input(f"Are you sure you want to delete user '{username}' (ID: {user_id})? (y/n): ")
        if confirm.lower() != 'y':
            print("Deletion cancelled.")
            return False
            
        # Proceed with deletion
        cur.execute("""
            DELETE FROM PITK3 
            WHERE id = %s
            RETURNING id
        """, (user_id,))
        
        if cur.rowcount > 0:
            db.conn.commit()
            print(f"Successfully deleted user '{username}' (ID: {user_id})")
            return True
        else:
            print("No user was deleted.")
            return False
            
    except Exception as e:
        print(f"Error deleting user: {e}")
        if 'db' in locals() and hasattr(db, 'conn') and db.conn is not None:
            db.conn.rollback()
        return False

def main():
    print("=== User Deletion Tool ===\n")
    
    # List all users
    users = list_users()
    if not users:
        return
        
    # Get user ID to delete
    try:
        user_id = input("\nEnter the ID of the user to delete (or 'q' to quit): ")
        if user_id.lower() == 'q':
            print("Operation cancelled.")
            return
            
        user_id = int(user_id)
        
        # Check if user ID exists
        if not any(user['id'] == user_id for user in users):
            print(f"Error: No user found with ID {user_id}")
            return
            
        # Delete the user
        delete_user(user_id)
        
    except ValueError:
        print("Error: Please enter a valid user ID (number).")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'db' in locals() and hasattr(db, 'conn') and db.conn is not None:
            db.conn.close()

if __name__ == "__main__":
    main()
