import psycopg2
import json

def show_database_structure():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com"
        )
        
        with conn.cursor() as cur:
            # Get table names
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()
            
            print("=== DATABASE STRUCTURE ===\n")
            
            # Show structure and data for each table
            for table in tables:
                table_name = table[0]
                print(f"\n=== Table: {table_name} ===")
                
                # Show columns
                cur.execute(f"""
                    SELECT column_name, data_type, is_nullable, 
                           character_maximum_length, numeric_precision
                    FROM information_schema.columns 
                    WHERE table_name = %s
                """, (table_name,))
                columns = cur.fetchall()
                print("\nColumns:")
                for col in columns:
                    print(f"- {col[0]} ({col[1]}) - Nullable: {col[2]}")
                    if col[3]:
                        print(f"  Max Length: {col[3]}")
                    if col[4]:
                        print(f"  Precision: {col[4]}")
                
                # Show sample data (first 5 rows)
                cur.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cur.fetchall()
                print("\nSample Data:")
                for row in rows:
                    print(f"- Row: {row}")
                    
                # For users table, show user_data structure
                if table_name == 'users':
                    cur.execute("""
                        SELECT id, user_data->'account'->>'username' as username,
                               user_data->'account'->>'password' as password,
                               user_data->'account'->'profile'->>'email' as email,
                               user_data->'account'->'profile'->>'phone' as phone
                        FROM users
                        LIMIT 5
                    """)
                    user_rows = cur.fetchall()
                    print("\nUser Data Structure:")
                    for user in user_rows:
                        print(f"- User ID: {user[0]}")
                        print(f"  Username: {user[1]}")
                        print(f"  Password: {user[2]}")
                        print(f"  Email: {user[3]}")
                        print(f"  Phone: {user[4]}")
                        print()
                        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== Fetching Database Structure ===\n")
    show_database_structure()
    print("\n=== Process Completed ===")
