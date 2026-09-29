import re

with open("api/router.py", "r", encoding="utf-8") as f:
    code = f.read()

patch = """        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        ext = file_path.suffix.lower()
        if ext in ['.pdf', '.docx', '.txt', '.xlsx']:
            try:
                from memory.ingestor import ingest_pdf
                logger.info(f"Auto-ingesting uploaded document: {file_path}")
                ingest_pdf(str(file_path))
            except Exception as e:
                logger.error(f"Failed to auto-ingest document {file_path}: {e}")
                
        prompt = f"[File Attached: {file_path}]\\n\\n{prompt}\""""

# Since the last regex failed, let's just find the line directly
idx = code.find('        prompt = f"[File Attached: {file_path}\\n\\n{prompt}"')
if idx == -1:
    idx = code.find('prompt = f"[File Attached: {file_path}]')

if idx != -1:
    start_idx = code.rfind('        with open(file_path, "wb") as buffer:', 0, idx)
    end_idx = code.find('\n', idx)
    
    code = code[:start_idx] + patch + code[end_idx:]

with open("api/router.py", "w", encoding="utf-8") as f:
    f.write(code)
