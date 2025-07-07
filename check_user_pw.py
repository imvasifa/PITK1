# Script to check user password data
import psycopg2
import bcrypt

def check_user():
    try:
        # Connect to PostgreSQL directly
        conn = psycopg2.connect(
            dbname="pitk3_db",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        
        cur = conn.cursor()
        
        # Query for user 'zxcv'
        cur.execute("""
            SELECT id, username, password, 
                   user_data->'account'->>'password' as json_password
            FROM PITK3 
            WHERE user_data->'account'->>'username' = 'zxcv' 
               OR username = 'zxcv'
            LIMIT 1
        """)
        
        user = cur.fetchone()
        if not user:
            print("❌ User 'zxcv' not found")
            return
            
        user_id, username, db_password, json_password = user
        
        print(f"\n=== User: {username} (ID: {user_id}) ===")
        print(f"Database password hash: {db_password}")
        print(f"JSON password hash: {json_password}")
        
        # Check if 'ccc' is the correct password
        password_to_check = 'ccc'  # The password you're trying to verify
        
        # Check database password
        if db_password and isinstance(db_password, str) and db_password.startswith('$2b$'):
            if bcrypt.checkpw(password_to_check.encode('utf-8'), db_password.encode('utf-8')):
                print("\n✅ Password 'ccc' matches the database password hash")
            else:
                print("\n❌ Password 'ccc' does NOT match the database password hash")
        
        # Check JSON password
        if json_password and isinstance(json_password, str) and json_password.startswith('$2b$'):
            if bcrypt.checkpw(password_to_check.encode('utf-8'), json_password.encode('utf-8')):
                print("✅ Password 'ccc' matches the JSON password hash")
            else:
                print("❌ Password 'ccc' does NOT match the JSON password hash")
        
        # If both hashes exist but don't match
        if db_password and json_password and db_password != json_password:
            print("\n⚠️  Warning: The password hashes in the database and JSON don't match!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
            
if __name__ == "__main__":
    check_user()
