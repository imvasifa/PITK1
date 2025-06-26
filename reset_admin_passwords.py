import psycopg2
import json

def reset_admin_passwords():
    admin_users = [
        {"id": 1, "username": "rahim"},
        {"id": 2, "username": "indianplans"},
        {"id": 3, "username": "imjjrobo"}
    ]
    
    conn = None
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com"
        )
        
        # Start a new transaction
        conn.rollback()
        
        for user in admin_users:
            try:
                with conn.cursor() as cur:
                    # Get current user data
                    cur.execute("""
                        SELECT user_data 
                        FROM users 
                        WHERE id = %s AND user_data->'account'->>'username' = %s
                        FOR UPDATE
                    """, (user['id'], user['username']))
                    
                    result = cur.fetchone()
                    if not result:
                        print(f"❌ User {user['username']} (ID: {user['id']}) not found")
                        continue
                    
                    # Update the password to 'ccc' in plain text
                    user_data = result[0]
                    user_data['account']['password'] = 'ccc'
                    
                    # Update the user in the database
                    cur.execute("""
                        UPDATE users 
                        SET user_data = %s
                        WHERE id = %s
                        RETURNING id, user_data->'account'->>'username' as username
                    """, (json.dumps(user_data), user['id']))
                    
                    updated = cur.fetchone()
                    if updated:
                        print(f"✅ Updated password to 'ccc' for {updated[1]} (ID: {updated[0]})")
                    else:
                        print(f"❌ Failed to update {user['username']}")
                        
                    # Commit after each user to prevent transaction issues
                    conn.commit()
                    
            except Exception as e:
                print(f"❌ Error updating {user['username']}: {e}")
                if conn is not None:
                    conn.rollback()
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    print("=== Resetting Admin Passwords to 'ccc' ===\n")
    reset_admin_passwords()
    print("\n=== Process Completed ===")
