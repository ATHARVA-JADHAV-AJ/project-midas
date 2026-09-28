import json
import bcrypt

try:
    with open('users.json', 'r') as f:
        users = json.load(f)
except:
    users = {}

pw = b"admin123"
hashed = bcrypt.hashpw(pw, bcrypt.gensalt()).decode('utf-8')
users["admin"] = {
    "hashed_password": hashed,
    "role": "admin"
}

with open('users.json', 'w') as f:
    json.dump(users, f, indent=2)

print("Admin password reset successfully.")
