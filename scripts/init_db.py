import json
import sqlite3
import os

DB_PATH = os.getenv("MIDAS_RBAC_DB", "./midas_identity.db")

def init():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'analyst', 'default')),
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            try:
                users = json.load(f)
            except:
                users = {}
        for username, data in users.items():
            role = data.get("role", "default")
            # Enforce strict 3 roles
            if role not in ('admin', 'analyst', 'default'):
                role = 'default'
            
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                    (username, data["hashed_password"], role)
                )
            except Exception as e:
                print(f"Failed to insert {username}: {e}")
        conn.commit()
        print(f"Migrated users.json to {DB_PATH}")
    else:
        print("No users.json found.")
    conn.close()

if __name__ == "__main__":
    init()
