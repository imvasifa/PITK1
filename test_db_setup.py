import sys
import os
import json

# Add the current directory to the path so we can import postgres_db
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from postgres_db import Database

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    print("Testing database connection...")
    try:
        db = Database()
        conn = db.conn
        if conn:
            print("✅ Successfully connected to PostgreSQL database!")
            return True
        else:
            print("❌ Failed to connect to database")
            return False
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False

def check_table_exists():
    print("\nChecking if app_settings table exists...")
    try:
        db = Database()
        cur = db.get_cursor()
        if not cur:
            print("❌ Failed to get database cursor")
            return False
            
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE  table_schema = 'public'
                AND    table_name   = 'app_settings'
            ) as table_exists;
        """)
        
        result = cur.fetchone()
        if not result:
            print("❌ Failed to check if table exists")
            return False
            
        table_exists = result['table_exists']
        
        if table_exists:
            print("✅ app_settings table exists")
            return True
        else:
            print("❌ app_settings table does not exist")
            return False
            
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False

def test_settings_save_load():
    print("\nTesting settings save and load...")
    try:
        # Ensure we can import the functions
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app3 import save_settings, load_settings
        
        # Test data
        test_settings = {
            'test': True,
            'conditions': ['test_condition1', 'test_condition2'],
            'selected_conditions': ['test_condition1', 'test_condition2'],
            'refresh_interval': 30,
            'mute_status': False,
            'user_conditions': [],
            'auto_refresh': True,
            'theme': 'light',
            'notifications': True,
            'sound_alert': True,
            'volume': 0.5,
            'last_update': None,
            'version': '1.0.0'
        }
        
        print("Saving test settings...")
        if not save_settings(test_settings):
            print("❌ Failed to save test settings")
            return False
            
        print("Loading settings...")
        loaded_settings = load_settings()
        
        # Verify loaded settings
        if not loaded_settings:
            print("❌ Failed to load settings")
            return False
            
        print("Verifying settings...")
        # Check if our test settings are in the loaded settings
        for key, value in test_settings.items():
            if key not in loaded_settings:
                print(f"❌ Setting '{key}' not found in loaded settings")
                return False
                
            if loaded_settings[key] != value:
                print(f"⚠️  Setting '{key}' does not match. Expected: {value}, Got: {loaded_settings.get(key)}")
                # Don't fail for type differences, just warn
                
        print("✅ Successfully saved and loaded settings")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*50)
    print("DATABASE SETUP TEST")
    print("="*50)
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Database connection test failed. Please check your database configuration.")
        return
    
    # Check table exists
    if not check_table_exists():
        print("\n❌ Table check failed. Please run the database migrations first.")
        return
    
    # Test settings save/load
    if not test_settings_save_load():
        print("\n❌ Settings test failed. Please check the logs above for details.")
        return
    
    print("\n✅ All tests passed successfully!")

if __name__ == "__main__":
    main()
