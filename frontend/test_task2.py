import requests
API_URL = "http://api:8000"
res = requests.post(f"{API_URL}/auth/token", json={"username": "admin", "password": "admin123"})
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
res = requests.post(f"{API_URL}/tasks", data={"prompt": "write a python hello world"}, headers=headers)
print("NO FILE POST STATUS:", res.status_code)
files = {"file": ("test.txt", b"hello", "text/plain")}
res2 = requests.post(f"{API_URL}/tasks", data={"prompt": "with file"}, files=files, headers=headers)
print("FILE POST STATUS:", res2.status_code)
