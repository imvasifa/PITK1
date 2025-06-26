import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.conn = None
        self._connection_initialized = False
        try:
            # Using the connection string from your dbPostgress.txt
            self.conn = psycopg2.connect(
                dbname="pitk",
                user="pitk_user",
                password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
                host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com",
                port="5432"
            )
            
            # Test the connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                if result[0] == 1:
                    if not hasattr(Database, '_connection_printed'):
                        print("✅ Successfully connected to PostgreSQL!")
                        print("✅ PostgreSQL connection test successful")
                        Database._connection_printed = True
                else:
                    print("❌ PostgreSQL connection test failed")
                    
        except Exception as e:
            print(f"❌ Could not connect to PostgreSQL: {e}")
            raise
    
    def get_cursor(self):
        if not self.conn or self.conn.closed != 0:
            self._initialize()
        return self.conn.cursor(cursor_factory=RealDictCursor)
    
    def close(self):
        if self.conn:
            self.conn.close()
            print("PostgreSQL connection closed")

# Create a single instance
db = Database()
