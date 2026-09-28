import sqlite3
import os

DB_PATH = os.getenv("MIDAS_RBAC_DB", "./midas_identity.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
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

def get_user(username: str):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

def create_user(username: str, hashed_password: str, role: str):
    if role not in ('admin', 'analyst', 'default'):
        raise ValueError("Invalid role")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
            (username, hashed_password, role)
        )
        conn.commit()
        return cursor.lastrowid
