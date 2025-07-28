import psycopg2
from psycopg2.extras import RealDictCursor

def test_connection():
    try:
        conn = psycopg2.connect(
            dbname="neondb",
            user="neondb_owner",
            password="npg_f7Lrs1OMVFjX",
            host="ep-green-field-a1hgytyd-pooler.ap-southeast-1.aws.neon.tech",
            port="5432",
            sslmode="require"
        )
        
        with conn.cursor() as cur:
            # Simple query to verify connection
            cur.execute("SELECT version()")
            version = cur.fetchone()
            print("✅ Connection successful!")
            print(f"PostgreSQL version: {version[0]}")
            
            # Check if tables exist
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()
            print("\nTables in the database:")
            for table in tables:
                print(f"- {table[0]}")
            
        conn.close()
        return True
        
    except Exception as e:
        print("❌ Connection failed!")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()