with open("api/router.py", "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("from fastapi import APIRouter", "from fastapi import APIRouter, BackgroundTasks")

with open("api/router.py", "w", encoding="utf-8") as f:
    f.write(code)
