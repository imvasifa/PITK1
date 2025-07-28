import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

def test_connection():
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL from environment
        db_url = os.getenv('DATABASE_URL')
        
        if not db_url:
            print("❌ DATABASE_URL not found in .env file")
            return
            
        print("🔍 Testing database connection...")
        
        # Connect to the database
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test query
        cur.execute("SELECT version()")
        db_version = cur.fetchone()
        print(f"✅ Connected to PostgreSQL {db_version['version']}")
        
        # List all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row['table_name'] for row in cur.fetchall()]
        print(f"\n📋 Database tables: {', '.join(tables) if tables else 'No tables found'}")
        
        # Close connection
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error connecting to the database: {str(e)}")

if __name__ == "__main__":
    test_connection()
