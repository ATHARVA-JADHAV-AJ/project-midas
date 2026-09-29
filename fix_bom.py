import os
import codecs

files = ["api/router.py", "frontend/app.py"]

for f in files:
    if os.path.exists(f):
        with open(f, "rb") as file:
            content = file.read()
        if content.startswith(codecs.BOM_UTF8):
            content = content[len(codecs.BOM_UTF8):]
            with open(f, "wb") as file:
                file.write(content)
            print(f"Removed BOM from {f}")
