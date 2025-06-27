import sys
import json
import psycopg2
from postgres_db import db

def test_db_connection():
    print("=== Testing Database Connection ===")
    try:
        # Get raw connection to test
        conn = db.get_connection()
        if not conn:
            print("❌ Failed to get database connection")
            return False
            
        print("✅ Successfully connected to database")
        
        # Test basic query
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()
            print(f"✅ Database version: {version[0]}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_tables():
    print("\n=== Checking Database Tables ===")
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            # Get list of all tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            if not tables:
                print("❌ No tables found in the database")
                return
                
            print(f"Found {len(tables)} tables:")
            for table in tables:
                print(f"- {table}")
                
                # Show table structure
                cur.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
                
                columns = cur.fetchall()
                print(f"  Columns ({len(columns)}):")
                for col in columns:
                    print(f"    - {col[0]} ({col[1]})")
                
                # Show row count
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  Rows: {count}")
                
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        import traceback
        traceback.print_exc()

def check_users_data():
    print("\n=== Checking Users Data ===")
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            # Check if users table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
            """)
            users_table_exists = cur.fetchone()[0]
            
            if not users_table_exists:
                print("❌ Users table does not exist")
                return
                
            # Get user count
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            print(f"Found {count} users in the database")
            
            if count > 0:
                # Get first few users
                cur.execute("""
                    SELECT id, user_data->'account'->>'username' as username,
                           user_data->'account'->>'email' as email,
                           created_at
                    FROM users 
                    LIMIT 5
                """)
                
                users = cur.fetchall()
                print("\nSample users:")
                for user in users:
                    print(f"- ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Created: {user[3]}")
                    
    except Exception as e:
        print(f"❌ Error checking users data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting database diagnostics...\n")
    
    if test_db_connection():
        check_tables()
        check_users_data()
    
    input("\nPress Enter to exit...")
