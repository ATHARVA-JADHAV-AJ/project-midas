import re

with open("core/nodes/reasoner.py", "r", encoding="utf-8") as f:
    code = f.read()

patch = """    base += (
        "\\nRequirements:\\n"
        "- MUST wrap the Python script in ```python and ``` markdown fences\\n"
        "- DO NOT write conversational filler. Only output code.\\n"
        "- DO NOT attempt to read or parse uploaded files (like PDFs) in your code! The extracted text is already provided in the context. Rely strictly on the context.\\n"
        "- Use python-docx to create .docx files, save to ./outputs/\\n"
        "- Use openpyxl to create .xlsx files, save to ./outputs/\\n"
        "- DO NOT USE `import` statements! math, json, datetime, collections, re, uuid, os, Document, openpyxl are PRE-LOADED in the global namespace.\\n"
        "- All file paths must use ./outputs/ prefix\\n"
        "- The script must be self-contained and terminate on its own\\n"
    )"""

code = re.sub(r'    base \+= \(\n        "\\nRequirements:\\n".*?terminate on its own\\n"\n    \)', patch, code, flags=re.DOTALL)

with open("core/nodes/reasoner.py", "w", encoding="utf-8") as f:
    f.write(code)
