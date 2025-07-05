import psycopg2
import sys
import os
from getpass import getpass
from psycopg2 import sql
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """Create and return a database connection using application config."""
    try:
        # Get database URL from environment variables or use default
        db_url = os.getenv('DATABASE_URL')
        
        if db_url:
            # Handle different database URL formats
            if db_url.startswith('postgresql://'):
                conn = psycopg2.connect(db_url, sslmode='require')
            else:
                conn = psycopg2.connect(db_url)
        else:
            # Fallback to individual environment variables
            conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'your_database_name'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432')
            )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def list_users(conn):
    """List all users in the database."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, 
                       user_data->'account'->>'username' as username,
                       user_data->'account'->'profile'->>'email' as email
                FROM users
                ORDER BY id
            """)
            users = cur.fetchall()
            
            if not users:
                print("No users found in the database.")
                return []
                
            print("\n=== LIST OF USERS ===")
            for user in users:
                print(f"ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
            print("\n")
            return users
            
    except Exception as e:
        print(f"Error listing users: {e}")
        return []

def delete_user(conn, user_id):
    """Delete a user by ID."""
    try:
        with conn.cursor() as cur:
            # First, get the username for confirmation
            cur.execute("""
                SELECT user_data->'account'->>'username' as username
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            if not result:
                print(f"No user found with ID: {user_id}")
                return False
                
            username = result[0]
            
            # Ask for confirmation
            confirm = input(f"Are you sure you want to delete user '{username}' (ID: {user_id})? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Deletion cancelled.")
                return False
                
            # Proceed with deletion
            cur.execute("""
                DELETE FROM users
                WHERE id = %s
                RETURNING id, user_data->'account'->>'username' as username
            """, (user_id,))
            
            # Debug: Print the SQL query and parameters
            print(f"Executing DELETE query for user ID: {user_id}")
            
            deleted = cur.fetchone()
            if deleted:
                conn.commit()
                print(f"Successfully deleted user '{deleted[1]}' (ID: {deleted[0]})")
                return True
            else:
                print("No user was deleted.")
                return False
                
    except Exception as e:
        print(f"Error deleting user: {e}")
        conn.rollback()
        return False

def delete_all_users(conn):
    """Delete all users from the database with confirmation."""
    try:
        # Get count of users
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            
            if count == 0:
                print("No users to delete.")
                return
                
            # List all users that will be deleted
            print("\n=== USERS TO BE DELETED ===")
            cur.execute("""
                SELECT id, user_data->'account'->>'username' as username
                FROM users
                ORDER BY id
            """)
            for user in cur.fetchall():
                print(f"ID: {user[0]}, Username: {user[1]}")
            print("\n")
            
            # Ask for confirmation
            confirm = input(f"WARNING: This will delete ALL {count} users listed above. Are you sure? (type 'DELETE ALL' to confirm): ")
            if confirm != 'DELETE ALL':
                print("Deletion cancelled.")
                return
                
            # Get admin confirmation
            admin_confirm = input("Type 'CONFIRM DELETION' to proceed (this cannot be undone): ")
            if admin_confirm != 'CONFIRM DELETION':
                print("Deletion cancelled.")
                return
                
            # Proceed with deletion
            deleted_count = 0
            try:
                cur.execute("DELETE FROM users")
                deleted_count = cur.rowcount
                conn.commit()
                print(f"Successfully deleted {deleted_count} users.")
            except Exception as e:
                conn.rollback()
                print(f"Error during deletion: {e}")
                print("No users were deleted due to an error.")
            
    except Exception as e:
        print(f"Error deleting users: {e}")
        conn.rollback()

def main():
    print("=== User Management Tool ===\n")
    
    # Connect to database using environment config
    print("Connecting to database...")
    try:
        conn = get_db_connection()
        print("Connected to database successfully!\n")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Please check your .env file or database configuration.")
        sys.exit(1)
    
    while True:
        print("\nOptions:")
        print("1. List all users")
        print("2. Delete a user by ID")
        print("3. Delete all users")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == '1':
            list_users(conn)
        elif choice == '2':
            try:
                user_id = int(input("Enter user ID to delete: "))
                delete_user(conn, user_id)
            except ValueError:
                print("Please enter a valid user ID (number).")
        elif choice == '3':
            delete_all_users(conn)
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")
    
    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
