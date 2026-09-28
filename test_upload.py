import requests

url = "http://api:8000/tasks"
headers = {"Authorization": "Bearer admin"} # Note: invalid token, but it should hit the API and give 401, not Network Error
files = {"file": ("test.txt", b"hello world", "text/plain")}
data = {"prompt": "analyze this"}

try:
    res = requests.post(url, data=data, files=files, headers=headers)
    print("STATUS:", res.status_code)
    print("RESPONSE:", res.text)
except Exception as e:
    print("NETWORK ERROR:", str(e))
