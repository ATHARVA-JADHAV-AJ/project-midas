import requests
API_URL = "http://localhost:8000"
res = requests.post(f"{API_URL}/tasks", data={"prompt": "write a python hello world script"})
print("STATUS", res.status_code)
print("TEXT", res.text)
