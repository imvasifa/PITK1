from app3 import save_user

def create_user():
    print("=== Create New User ===")
    username = input("Enter username: ")
    password = input("Enter password: ")
    email = input("Enter email (optional): ")
    
    if not username or not password:
        print("❌ Username and password are required!")
        return
        
    print("\nCreating user...")
    user_id = save_user(username, password, email)
    
    if user_id:
        print(f"✅ User created successfully with ID: {user_id}")
        print(f"Username: {username}")
        print("Password: [hidden]")
    else:
        print("❌ Failed to create user")

if __name__ == "__main__":
    create_user()
