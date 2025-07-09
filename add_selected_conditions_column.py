import sys
from app3 import db

def add_selected_conditions_column():
    try:
        print("Adding selected_conditions column to PITK3 table...")
        cur = db.get_cursor()
        
        # Check if column already exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='pitk3' AND column_name='selected_conditions';
        """)
        
        if cur.fetchone():
            print("Column 'selected_conditions' already exists.")
            return True
            
        # Add the column
        cur.execute("""
            ALTER TABLE PITK3 
            ADD COLUMN selected_conditions TEXT[] DEFAULT '{}'::TEXT[];
        """)
        
        db.conn.commit()
        print("✅ Successfully added selected_conditions column.")
        return True
        
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        if db.conn:
            db.conn.rollback()
        return False
    finally:
        if db.conn:
            db.conn.close()

if __name__ == "__main__":
    if add_selected_conditions_column():
        sys.exit(0)
    else:
        sys.exit(1)
