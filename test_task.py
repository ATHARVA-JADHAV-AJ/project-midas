import time
import requests
import json

API_URL = "http://api:8000"

# 1. Login
res = requests.post(f"{API_URL}/auth/token", json={"username": "admin", "password": "admin123"})
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Submit task
res = requests.post(f"{API_URL}/tasks", data={"prompt": "write a python hello world"}, headers=headers)
task_id = res.json()["task_id"]
print("Task ID:", task_id)

# 3. Poll
for i in range(10):
    res = requests.get(f"{API_URL}/tasks/{task_id}", headers=headers)
    status = res.json()["status"]
    print(f"Status: {status}")
    if status in ["done", "failed", "waiting_approval"]:
        if status == "waiting_approval":
            print("Approving...")
            requests.post(f"{API_URL}/tasks/{task_id}/approve", headers=headers)
            time.sleep(2)
            res = requests.get(f"{API_URL}/tasks/{task_id}", headers=headers)
            print("Final Status:", res.json()["status"])
            if res.json()["status"] == "done":
                print("Result:", res.json()["result"])
        break
    time.sleep(1)

