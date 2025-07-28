import psycopg2
from postgres_db import db

try:
    # Get cursor
    cur = db.conn.cursor()
    
    # First, let's find the exact table name
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name ILIKE 'pitk3'
    """)
    table_info = cur.fetchone()
    if not table_info:
        print("❌ Error: Could not find PITK3 table")
        exit(1)
    
    actual_table_name = table_info[0]
    print(f"ℹ️ Found table: {actual_table_name}")
    
    # Add OTP column using the exact table name
    cur.execute(f"""
        ALTER TABLE "{actual_table_name}" 
        ADD COLUMN IF NOT EXISTS otp VARCHAR(10)
    """)
    db.conn.commit()
    print("✅ OTP column added successfully")
    
    # Verify with exact table name
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s 
        AND column_name = 'otp'
    """, (actual_table_name,))
    
    if cur.fetchone():
        print("✅ Verification: OTP column exists in the table")
    else:
        print("❌ Verification: OTP column was not found")
        
    # Show all columns for debugging
    print("\nAll columns in the table:")
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s
    """, (actual_table_name,))
    for col in cur.fetchall():
        print(f"- {col[0]} ({col[1]})")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    if 'db' in locals() and hasattr(db, 'conn'):
        db.conn.rollback()
finally:
    if 'cur' in locals():
        cur.close()

print("\nScript completed")