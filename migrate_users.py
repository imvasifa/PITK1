import json
import os
from datetime import datetime
from postgres_db import db

def create_users_table():
    """Create users table in PostgreSQL if it doesn't exist"""
    try:
        cur = db.get_cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                user_data JSONB
            )
        """)
        db.conn.commit()
        print("✅ Users table created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating users table: {e}")
        db.conn.rollback()
        return False

def migrate_users():
    try:
        # Read the users from JSON file
        with open('users.json', 'r') as f:
            users_data = json.load(f)
        
        cur = db.get_cursor()
        migrated_count = 0
        
        # Check if any users exist
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()['count'] > 0:
            print("⚠️  Users table already contains data. Migration aborted to prevent duplicates.")
            return
        
        # Migrate each user
        for user_id, user_data in users_data.items():
            try:
                account = user_data['account']
                
                # Prepare the user data for insertion
                user_record = {
                    'username': account['username'],
                    'password_hash': account['password'],  # In production, this should be hashed
                    'is_admin': False,  # Set admin status as needed
                    'user_data': json.dumps(user_data)  # Store the complete user data as JSONB
                }
                
                # Insert the user
                cur.execute("""
                    INSERT INTO users (username, password_hash, is_admin, user_data)
                    VALUES (%(username)s, %(password_hash)s, %(is_admin)s, %(user_data)s::jsonb)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING id
                """, user_record)
                
                if cur.rowcount > 0:
                    migrated_count += 1
                    print(f"✅ Migrated user: {account['username']}")
                
            except Exception as e:
                print(f"⚠️  Error migrating user {user_id}: {e}")
                db.conn.rollback()
                continue
        
        db.conn.commit()
        print(f"\n✅ Migration complete! {migrated_count} users migrated successfully.")
        
    except FileNotFoundError:
        print("❌ Error: users.json file not found")
    except json.JSONDecodeError:
        print("❌ Error: Invalid JSON format in users.json")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        db.conn.rollback()

if __name__ == "__main__":
    print("Starting user migration from JSON to PostgreSQL...\n")
    if create_users_table():
        migrate_users()
    print("\nMigration process completed.")
