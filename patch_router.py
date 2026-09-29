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
                
        prompt = f"[File Attached: {file_path}]\\n\\n{prompt}"""

code = re.sub(r'        with open\(file_path, "wb"\) as buffer:\n            shutil\.copyfileobj\(file\.file, buffer\)\n        prompt = f"\[File Attached: \{file_path\}\]\\n\\n\{prompt\}"', patch, code)

with open("api/router.py", "w", encoding="utf-8") as f:
    f.write(code)
