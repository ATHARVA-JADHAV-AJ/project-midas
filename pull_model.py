import requests

url = "http://localhost:11434/api/pull"
data = {"name": "qwen2.5:0.5b"}

try:
    print("Pulling qwen2.5:0.5b...")
    for line in requests.post(url, json=data, stream=True).iter_lines():
        if line:
            print(line.decode())
except Exception as e:
    print("Error pulling:", e)
