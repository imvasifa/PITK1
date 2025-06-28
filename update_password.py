from flask_bcrypt import Bcrypt
import json
from postgres_db import db

# Initialize bcrypt
bcrypt = Bcrypt()

def update_user_password(username, new_password):
    try:
        # Generate a bcrypt hash of the new password using flask_bcrypt
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        print(f"🔑 Updating password for user: {username}")
        print(f"🔑 New password hash: {hashed_password[:20]}...")
        
        # Update the user's password in the database
        cur = db.get_cursor()
        if not cur:
            print("❌ Database connection error")
            return False
            
        # First, get the current user data
        cur.execute("""
            SELECT id, user_data FROM users 
            WHERE user_data->'account'->>'username' = %s
        """, (username,))
        
        user = cur.fetchone()
        if not user:
            print(f"❌ User '{username}' not found")
            return False
            
        # Convert to dictionary if needed
        if not isinstance(user, dict):
            columns = [desc[0] for desc in cur.description]
            user = dict(zip(columns, user))
        
        # Update the password in the user_data
        user_data = user['user_data']
        user_data['account']['password'] = hashed_password
        
        # Save the updated user data
        cur.execute("""
            UPDATE users 
            SET user_data = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id
        """, (json.dumps(user_data), user['id']))
        
        db.conn.commit()
        
        if cur.rowcount > 0:
            print(f"✅ Successfully updated password for user: {username}")
            return True
        else:
            print("❌ Failed to update password")
            return False
            
    except Exception as e:
        print(f"❌ Error updating password: {e}")
        import traceback
        traceback.print_exc()
        if 'db' in locals() and db.conn:
            db.conn.rollback()
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python update_password.py <username> <new_password>")
        sys.exit(1)
        
    username = sys.argv[1]
    password = sys.argv[2]
    
    update_user_password(username, password)
