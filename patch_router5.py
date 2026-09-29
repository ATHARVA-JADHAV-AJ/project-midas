import re

with open("api/router.py", "r", encoding="utf-8") as f:
    code = f.read()

# Add BackgroundTasks to imports
code = re.sub(r'from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket.*', 'from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket, BackgroundTasks, UploadFile', code)

# Add BackgroundTasks to submit_task signature
code = re.sub(r'async def submit_task\(\n    request: Request,\n    \n\):', 'async def submit_task(\n    request: Request,\n    background_tasks: BackgroundTasks,\n):', code)

# Swap run_in_threadpool with BackgroundTasks
code = re.sub(r'await run_in_threadpool\(ingest_pdf, str\(file_path\)\)', 'background_tasks.add_task(ingest_pdf, str(file_path))', code)

with open("api/router.py", "w", encoding="utf-8") as f:
    f.write(code)
