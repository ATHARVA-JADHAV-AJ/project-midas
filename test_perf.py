import time
import requests

API_URL = "http://localhost:8000"

start = time.time()
print("1. Submitting Task...")
res = requests.post(f"{API_URL}/tasks", data={"prompt": "write a python hello world script"})
task_id = res.json()["task_id"]
print(f"Task ID: {task_id}, Response Code: {res.status_code}")
submit_time = time.time()
print(f"Submit latency: {(submit_time - start)*1000:.2f} ms")

print("\n2. Polling for completion...")
for i in range(20):
    r = requests.get(f"{API_URL}/tasks/{task_id}")
    status = r.json()["status"]
    print(f"Status: {status}")
    if status == "waiting_approval":
        print("Approving HITL...")
        requests.post(f"{API_URL}/tasks/{task_id}/approve")
    elif status == "done":
        end = time.time()
        print(f"\nSUCCESS! Total E2E time: {end - start:.2f} seconds")
        break
    time.sleep(1)
