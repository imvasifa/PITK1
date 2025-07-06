import psycopg2
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env file")

# Parse the DATABASE_URL
result = urlparse(DATABASE_URL)
DB_HOST = result.hostname
DB_NAME = result.path.lstrip('/')
DB_USER = result.username
DB_PASS = result.password
DB_PORT = result.port or 5432

def create_pitk3_table():
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS PITK3 (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL,
                user_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        print('✅ Table PITK3 created successfully.')
    except Exception as e:
        print(f'❌ Error creating PITK3 table: {e}')
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_pitk3_table()

