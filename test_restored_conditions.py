#!/usr/bin/env python3
"""
Test script to verify the restored user conditions functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from postgres_db import db
import json

def test_restored_conditions():
    """Test the restored load_user_conditions function"""
    
    print("🧪 Testing restored user conditions functionality...")
    
    try:
        # Get database connection
        conn = db.conn
        if not conn:
            print("❌ Could not get database connection")
            return
        
        cursor = conn.cursor()
        
        # Get user with ID 3 (imjjrobo)
        cursor.execute("""
            SELECT id, user_data 
            FROM users 
            WHERE id = 3
        """)
        
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            print("❌ User with ID 3 not found")
            return
        
        user_id, user_data = result
        print(f"✅ Found user {user_id}")
        
        # Parse user_data if it's a string
        if isinstance(user_data, str):
            try:
                user_data = json.loads(user_data)
            except json.JSONDecodeError:
                print("❌ Failed to parse user_data JSON")
                return
        
        # Extract conditions
        conditions = user_data.get('account', {}).get('conditions', [])
        print(f"✅ Found {len(conditions)} conditions in user_data")
        
        for i, condition in enumerate(conditions):
            print(f"  {i+1}. {condition.get('name', 'Unknown')} (ID: {condition.get('id', 'Unknown')})")
        
        # Test the load_user_conditions function
        print("\n🔧 Testing load_user_conditions function...")
        
        # Import the function
        from app3 import load_user_conditions
        
        # Call the function
        loaded_conditions = load_user_conditions(3)
        print(f"✅ load_user_conditions returned {len(loaded_conditions)} conditions")
        
        for i, condition in enumerate(loaded_conditions):
            print(f"  {i+1}. {condition.get('name', 'Unknown')} (ID: {condition.get('id', 'Unknown')})")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_restored_conditions() 