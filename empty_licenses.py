import psycopg2

def empty_licenses():
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com"
        )
        
        # Create a cursor
        with conn.cursor() as cur:
            # Truncate the licenses table
            cur.execute("TRUNCATE TABLE licenses;")
            conn.commit()
            print("✅ Successfully emptied the licenses table")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    empty_licenses()
