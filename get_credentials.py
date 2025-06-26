import psycopg2
from psycopg2.extras import DictCursor

def get_user_credentials():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com",
            cursor_factory=DictCursor
        )
        
        with conn.cursor() as cur:
            # Get usernames and passwords from user_data JSONB
            cur.execute("""
                SELECT 
                    id,
                    username,
                    user_data->'account'->>'password' as password
                FROM users
                ORDER BY id
            """)
            
            users = cur.fetchall()
            
            if not users:
                print("No users found in the database")
                return
                
            print("\nUser Credentials:")
            print("-" * 50)
            print(f"{'ID':<5} | {'Username':<20} | {'Password'}")
            print("-" * 50)
            
            for user in users:
                print(f"{user['id']:<5} | {user['username']:<20} | {user['password']}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🔐 Retrieving user credentials...")
    get_user_credentials()
