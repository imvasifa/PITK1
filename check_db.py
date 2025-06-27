import sys
import os
import json
from postgres_db import db

def list_tables():
    """List all tables in the database"""
    try:
        cur = db.get_cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]
        print("\n=== Tables in database ===")
        for table in tables:
            print(f"- {table}")
        return tables
    except Exception as e:
        print(f"Error listing tables: {e}")
        return []

def show_table_data(table_name):
    """Show data from a specific table"""
    try:
        cur = db.get_cursor()
        # First get column names
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s
        """, (table_name,))
        columns = [row[0] for row in cur.fetchall()]
        
        if not columns:
            print(f"No columns found for table {table_name}")
            return
            
        # Get data
        cur.execute(f"SELECT * FROM {table_name} LIMIT 10")
        rows = cur.fetchall()
        
        print(f"\n=== Data from {table_name} (first 10 rows) ===")
        print("Columns:", ", ".join(columns))
        print("-" * 50)
        
        for row in rows:
            # Convert row to dict for better display
            row_dict = dict(zip(columns, row))
            # Handle JSON fields
            for key, value in row_dict.items():
                if isinstance(value, dict):
                    row_dict[key] = json.dumps(value, indent=2)
            print(json.dumps(row_dict, indent=2))
            print("-" * 50)
            
    except Exception as e:
        print(f"Error showing data from {table_name}: {e}")

if __name__ == "__main__":
    print("Checking database contents...")
    tables = list_tables()
    
    if not tables:
        print("No tables found in the database.")
    else:
        for table in tables:
            show_table_data(table)
    
    input("\nPress Enter to exit...")
