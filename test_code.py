import time
import requests

API_URL = "http://localhost:8000"

res = requests.post(f"{API_URL}/tasks", data={"prompt": "write a python script to define an exp function. provide a long explanation after the code."})
task_id = res.json()["task_id"]

for i in range(20):
    r = requests.get(f"{API_URL}/tasks/{task_id}")
    status = r.json()["status"]
    if status == "done" or status == "failed":
        print(f"Status: {status}")
        print("Result:", r.json()["result"])
        break
    time.sleep(1)
