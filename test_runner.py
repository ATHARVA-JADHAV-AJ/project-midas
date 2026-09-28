import requests
import time
import os

API = 'http://midas_v35_api:8000'

tests = [
    ('test.pdf', 'give me a detailed analysis', 'pdf document -> document -> RAG'),
    ('test.xlsx', 'give me a detailed analysis', 'xlsx -> math -> code'),
    ('test.csv', 'calculate the average of col1', 'csv -> math -> code'),
    ('test.docx', 'give me a detailed analysis', 'docx -> document -> RAG'),
    ('test.png', 'extract text from this image', 'image -> vision'),
    ('empty.txt', 'give me a detailed analysis', '400 error expected'),
    ('corrupted.pdf', 'give me a detailed analysis', 'pdf -> document -> RAG (might fail to extract text)'),
    ('renamed_pdf.xlsx', 'analyze this spreadsheet', 'mismatch caught by magic bytes -> routes as pdf -> document'),
    ('renamed_xlsx.pdf', 'give me a detailed analysis', 'mismatch caught by magic bytes -> routes as xlsx -> math'),
    (None, 'what is MRPL?', 'chat'),
    ('test.pdf', 'calculate the average of col1', 'pdf -> mismatch caught before execution -> error message'),
]

for filename, prompt, desc in tests:
    print(f'\n--- Testing: {filename} with "{prompt}" ---')
    print(f'Expected: {desc}')
    
    files = None
    if filename:
        path = f'/app/test_files/{filename}'
        files = {'file': (filename, open(path, 'rb'), 'application/octet-stream')}
        
    try:
        res = requests.post(f'{API}/tasks', data={'prompt': prompt}, files=files)
        if res.status_code != 200:
            print(f'Upload failed: {res.status_code} {res.text}')
            continue
            
        task_id = res.json()['task_id']
        print(f'Task {task_id} queued. Polling...')
        
        while True:
            time.sleep(2)
            status_res = requests.get(f'{API}/tasks/{task_id}')
            if status_res.status_code != 200:
                print(f'Poll failed: {status_res.status_code}')
                break
            
            data = status_res.json()
            status = data['status']
            print(f'   ... {status}')
            if status in ('done', 'failed'):
                print(f'FINAL STATUS: {status}')
                print(f'Result/Error: {data.get("result")}')
                break
    except Exception as e:
        print(f'Test script error: {e}')
