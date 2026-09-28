"""End-to-end test: submit a task and poll for result."""
import time
import requests

API = "http://localhost:8000"

# Get token
tok_res = requests.post(f"{API}/auth/token", data={"username": "testuser", "password": "test1234"})
if tok_res.status_code != 200:
    # Try to find valid creds
    print(f"Login failed with operator: {tok_res.text}")
    # Try default
    tok_res = requests.post(f"{API}/auth/token", data={"username": "default", "password": "default123"})
    if tok_res.status_code != 200:
        print(f"Login failed with default too: {tok_res.text}")
        # Check what users exist
        import sqlite3, os
        db_path = os.getenv("MIDAS_RBAC_DB", "./midas_identity.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            rows = conn.execute("SELECT username, role FROM users").fetchall()
            print(f"Users in DB: {rows}")
            conn.close()
        else:
            print(f"DB not found at {db_path}")
        exit(1)

token = tok_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Submit task
prompt = "Calculate the Fourier series expansion for a square wave. Show all the mathematical steps and package it into a downloadable PDF."
task_res = requests.post(f"{API}/tasks", json={"prompt": prompt}, headers=headers)
if task_res.status_code != 200:
    # Try form data
    task_res = requests.post(f"{API}/tasks", data={"prompt": prompt}, headers=headers)

print(f"Task submitted: {task_res.status_code} {task_res.text}")
task_id = task_res.json().get("task_id")
if not task_id:
    exit(1)

# Poll
for i in range(60):
    time.sleep(2)
    status_res = requests.get(f"{API}/tasks/{task_id}", headers=headers)
    data = status_res.json()
    st = data.get("status")
    print(f"  [{i*2}s] Status: {st}")
    if st in ("done", "failed"):
        print(f"\n=== FINAL RESULT ===")
        print(f"Status: {st}")
        print(f"Result: {data.get('result', '')[:500]}")
        print(f"Output: {data.get('output_path', '')}")
        if data.get("error"):
            print(f"Error: {data['error']}")
        break
