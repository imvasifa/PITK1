import psycopg2

def reset_database():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com"
        )
        
        # Rollback any existing transaction
        conn.rollback()
        
        # Create a new cursor
        with conn.cursor() as cur:
            # Test the connection
            cur.execute("SELECT 1")
            result = cur.fetchone()
            if result and result[0] == 1:
                print("✅ Database connection reset and working correctly")
            else:
                print("❌ Database connection test failed")
                
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== Resetting Database Connection ===\n")
    reset_database()
    print("\n=== Process Completed ===")
