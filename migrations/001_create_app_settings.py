import os
import sys
import json

# Add the parent directory to the path so we can import postgres_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from postgres_db import Database

def run_migration():
    """Create the app_settings table if it doesn't exist"""
    print("Running migration: Create app_settings table")
    
    try:
        db = Database()
        cur = db.get_cursor()
        if not cur:
            print("❌ Failed to get database cursor")
            return False
        
        print("Creating app_settings table...")
        
        # Create the app_settings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY,
                settings JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create or replace the update_updated_at_column function
        cur.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Create the trigger
        cur.execute("""
            DROP TRIGGER IF EXISTS update_app_settings_updated_at ON app_settings;
            CREATE TRIGGER update_app_settings_updated_at
            BEFORE UPDATE ON app_settings
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
        
        # Insert default settings if table is empty
        cur.execute("SELECT COUNT(*) as count FROM app_settings")
        result = cur.fetchone()
        count = result['count'] if result and 'count' in result else 0
        
        print(f"Found {count} existing settings in the database")
        
        if count == 0:
            print("Inserting default settings...")
            default_settings = {
                'refresh_interval': 20,
                'mute_status': False,
                'conditions': [],
                'selected_conditions': [],
                'user_conditions': [],
                'auto_refresh': True,
                'theme': 'light',
                'notifications': True,
                'sound_alert': True,
                'volume': 0.5,
                'last_update': None,
                'version': '1.0.0'
            }
            
            cur.execute("""
                INSERT INTO app_settings (id, settings)
                VALUES (1, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (json.dumps(default_settings),))
        
        db.conn.commit()
        print("✅ Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        if db.conn:
            db.conn.rollback()
        return False

if __name__ == "__main__":
    # Create migrations directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    # Run the migration
    success = run_migration()
    sys.exit(0 if success else 1)
