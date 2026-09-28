from fastapi import FastAPI, Form, File, UploadFile
from fastapi.testclient import TestClient

app = FastAPI()

@app.post("/tasks")
async def tasks(prompt: str = Form(...), file: UploadFile | None = File(None)):
    return {"prompt": prompt, "has_file": bool(file)}

client = TestClient(app)

# Test with no files (application/x-www-form-urlencoded)
res1 = client.post("/tasks", data={"prompt": "hello"})
print("URL Encoded:", res1.status_code, res1.text)

# Test with empty files (multipart/form-data)
res2 = client.post("/tasks", data={"prompt": "hello"}, files={"file": ("", b"")})
print("Multipart Empty File:", res2.status_code, res2.text)

# Test with files=None but forcing multipart?
res3 = client.post("/tasks", data={"prompt": "hello"}, files={})
print("Multipart No File:", res3.status_code, res3.text)
