import psycopg2

def check_admin_password(username):
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com"
        )
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_data->'account'->>'username' as username,
                       user_data->'account'->>'password' as password
                FROM users 
                WHERE user_data->'account'->>'username' = %s
            """, (username,))
            
            user = cur.fetchone()
            if user:
                print(f"Found user: {user[1]} (ID: {user[0]})")
                print(f"Password: {user[2]}")
            else:
                print(f"User '{username}' not found in database")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== Checking Admin Password ===\n")
    check_admin_password("indianplans")
    print("\n=== Process Completed ===")
