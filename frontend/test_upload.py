import requests
url = "http://api:8000/tasks"
files = {"file": ("test.txt", b"hello", "text/plain")}
try:
    res = requests.post(url, data={"prompt": "test"}, files=files)
    print("STATUS", res.status_code)
except Exception as e:
    print("ERROR", str(e))
