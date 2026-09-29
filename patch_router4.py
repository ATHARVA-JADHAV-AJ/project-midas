with open("api/router.py", "r", encoding="utf-8") as f:
    code = f.read()

import re
code = re.sub(r'ingest_pdf\(str\(file_path\)\)', 'await run_in_threadpool(ingest_pdf, str(file_path))', code)
code = re.sub(r'from memory.ingestor import ingest_pdf', 'from memory.ingestor import ingest_pdf\n                from starlette.concurrency import run_in_threadpool', code)

with open("api/router.py", "w", encoding="utf-8") as f:
    f.write(code)
