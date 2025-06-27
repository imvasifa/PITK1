from postgres_db import db

# Get all users with their usernames and IDs
cur = db.get_cursor()
cur.execute("""
    SELECT id, user_data->'account'->>'username' as username 
    FROM users 
    ORDER BY id
""")

print("\n=== ALL USERS ===")
for row in cur.fetchall():
    print(f"ID: {row['id']}, Username: {row['username']}")

# Get detailed data for indianplans
print("\n=== DETAILED DATA FOR indianplans ===")
cur.execute("""
    SELECT * 
    FROM users 
    WHERE user_data->'account'->>'username' = 'indianplans'
""")

indianplans = cur.fetchone()
if indianplans:
    print("\nColumns:", [desc[0] for desc in cur.description])
    print("\nData:")
    for key, value in indianplans.items():
        print(f"{key}: {value}")
else:
    print("User 'indianplans' not found")
