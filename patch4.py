lines = []
with open("core/nodes/reasoner.py", "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if "- Use openpyxl" in line:
            lines.append('        "- Use openpyxl to create .xlsx files, save to /outputs/\\n"\n')
            lines.append('        "- DO NOT USE import statements! math, json, datetime, collections, re, uuid, os, Document, openpyxl are PRE-LOADED.\\n"\n')
        elif "- DO NOT USE import statements!" in line:
            pass # skip the bad line
        else:
            lines.append(line)

with open("core/nodes/reasoner.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
