import json
import psycopg2
from flask import Flask
from flask_bcrypt import Bcrypt

# Create a minimal Flask app for Bcrypt
app = Flask(__name__)
bcrypt = Bcrypt(app)

def reset_password():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname="pitk",
            user="pitk_user",
            password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
            host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com"
        )
        
        # First, rollback any existing transaction
        conn.rollback()
        
        # Generate a new strong password
        new_password = 'NewStrongPass123!@#'  # You can change this to any password you prefer
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Get current user data
        with conn.cursor() as cur:
            # Get current user data
            cur.execute("""
                SELECT user_data 
                FROM users 
                WHERE user_data->'account'->>'username' = 'imjjrobo'
            """)
            user_data = cur.fetchone()
            
            if not user_data:
                print("❌ User 'imjjrobo' not found")
                return
                
            # Update the password in user_data
            user_data = user_data[0]  # Get the JSON data
            user_data['account']['password'] = hashed_password
            
            # Update the user in the database
            cur.execute("""
                UPDATE users 
                SET user_data = %s::jsonb
                WHERE user_data->'account'->>'username' = 'imjjrobo'
                RETURNING id, user_data->'account'->>'username' as username
            """, (json.dumps(user_data),))
            
            result = cur.fetchone()
            if result:
                conn.commit()
                print("✅ Password reset successful")
                print(f"Username: imjjrobo")
                print(f"New Password: {new_password}")
            else:
                conn.rollback()
                print("❌ Failed to update password")
                
    except Exception as e:
        if 'conn' in locals() and conn is not None:
            conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

if __name__ == "__main__":
    print("=== Resetting Password for imjjrobo ===\n")
    reset_password()
