import json
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# --- CONFIG ---
from config import Config

def get_db_connection():
    uri = Config.DATABASE_URI
    parsed = urlparse(uri)
    dbname = parsed.path.lstrip('/')
    user = parsed.username
    password = parsed.password
    host = parsed.hostname
    port = parsed.port or 5432
    print(f"Connecting to DB with:")
    print(f"  host={host}")
    print(f"  port={port}")
    print(f"  dbname={dbname}")
    print(f"  user={user}")
    # Do not print password for security
    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )

def migrate_user_conditions():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    inserted = 0
    skipped = 0
    users_processed = 0
    print("🔄 Starting migration of user conditions...")
    
    # 1. Get all users and their user_data
    cur.execute("SELECT id, user_data FROM users")
    users = cur.fetchall()
    for user in users:
        user_id = user['id']
        user_data = user['user_data']
        users_processed += 1
        if not user_data:
            continue
        # Parse user_data if it's a string
        if isinstance(user_data, str):
            try:
                user_data = json.loads(user_data)
            except Exception as e:
                print(f"❌ Failed to parse user_data for user {user_id}: {e}")
                continue
        # Get conditions from user_data
        conditions = user_data.get('account', {}).get('conditions', [])
        if not conditions:
            continue
        for cond in conditions:
            # Check if this condition already exists for this user (by name and scan_clause)
            cur.execute(
                "SELECT 1 FROM user_conditions WHERE user_id = %s AND name = %s AND scan_clause = %s",
                (user_id, cond.get('name', ''), cond.get('scan_clause', ''))
            )
            if cur.fetchone():
                skipped += 1
                continue
            # Insert into user_conditions
            cur.execute(
                """
                INSERT INTO user_conditions (user_id, name, scan_clause, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                """,
                (user_id, cond.get('name', ''), cond.get('scan_clause', ''))
            )
            inserted += 1
        conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Migration complete. Users processed: {users_processed}, Conditions inserted: {inserted}, Skipped (duplicates): {skipped}")

if __name__ == "__main__":
    migrate_user_conditions() 