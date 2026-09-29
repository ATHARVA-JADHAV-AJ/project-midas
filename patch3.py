with open("core/nodes/reasoner.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
code = re.sub(
    r'"- Use openpyxl to create \.xlsx files, save to /outputs/\\n"|"- Use openpyxl to create \.xlsx files, save to /outputs/\n- DO NOT USE.*?"', 
    '"- Use openpyxl to create .xlsx files, save to /outputs/\\n"\n        "- DO NOT USE import statements! math, json, datetime, collections, re, uuid, os, Document, openpyxl are PRE-LOADED in the global namespace. Just use them directly.\\n"', 
    code, 
    flags=re.DOTALL
)

# Also fix the weird emojis "A'A,A" back to standard text
code = re.sub(r'A.*?no markdown fences', 'no markdown fences', code)

with open("core/nodes/reasoner.py", "w", encoding="utf-8") as f:
    f.write(code)
