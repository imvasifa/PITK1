import json
import psycopg2
import secrets
import string
from flask import Flask
from flask_bcrypt import Bcrypt

# Create a minimal Flask app for Bcrypt
app = Flask(__name__)
bcrypt = Bcrypt(app)

def get_old_users():
    """Fetch old users with their current password hashes."""
    try:
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com"
        )
        
        with conn.cursor() as cur:
            # Get all users with their current password hashes
            cur.execute("""
                SELECT 
                    id,
                    user_data->'account'->>'username' as username,
                    user_data->'account'->>'password' as password_hash,
                    user_data as user_data
                FROM users 
                WHERE id IN (1, 2, 3)
                ORDER BY id
            """)
            
            users = []
            for row in cur.fetchall():
                user_id, username, password_hash, user_data = row
                users.append({
                    'id': user_id,
                    'username': username,
                    'password_hash': password_hash,
                    'user_data': user_data
                })
            
            return users
            
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        return []
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

def update_user_password(user_id, hashed_password, user_data):
    """Update a user's password in the database."""
    try:
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com"
        )
        
        with conn.cursor() as cur:
            # Update the password in the user_data JSON
            user_data['account']['password'] = hashed_password
            
            # Update the user in the database
            cur.execute("""
                UPDATE users 
                SET user_data = %s::jsonb
                WHERE id = %s
                RETURNING id, user_data->'account'->>'username' as username
            """, (json.dumps(user_data), user_id))
            
            result = cur.fetchone()
            if result:
                conn.commit()
                return True, f"Updated password for user: {result[1]} (ID: {result[0]})"
            else:
                conn.rollback()
                return False, f"User with ID {user_id} not found"
                
    except Exception as e:
        if 'conn' in locals() and conn is not None:
            conn.rollback()
        return False, f"Error updating user {user_id}: {e}"
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

def generate_strong_password(length=16):
    """Generate a strong random password."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()_+=-'
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure password meets complexity requirements
        if (any(c.islower() for c in password) and 
            any(c.isupper() for c in password) and 
            any(c.isdigit() for c in password) and
            any(c in '!@#$%^&*()_+=-' for c in password)):
            return password

def main():
    print("=== Auto-updating Old User Passwords ===\n")
    
    # Get the list of old users
    users = get_old_users()
    
    if not users:
        print("No old users found or error fetching users.")
        return
    
    print("Found the following old users:")
    for user in users:
        print(f"- {user['username']} (ID: {user['id']})")
    
    confirm = input("\nThis will update passwords for all users. Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("\nGenerating and setting strong passwords...\n")
    
    for user in users:
        print(f"Updating {user['username']} (ID: {user['id']})...")
        print(f"Current password hash: {user['password_hash'] or 'None'}")
        
        # Generate a strong password
        password = generate_strong_password()
        
        # Generate password hash using bcrypt
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Update the user
        success, message = update_user_password(
            user['id'], 
            hashed_password, 
            user['user_data']
        )
        
        if success:
            print(f"✅ {message}")
            print(f"   New password: {password}")
            print(f"   New password hash: {hashed_password[:60]}...\n")
        else:
            print(f"❌ {message}")
            
    print("\n=== Passwords Updated Successfully ===")
    print("Please make sure to save these passwords in a secure location.")
    
    print("\nAll users processed.")

if __name__ == "__main__":
    main()
