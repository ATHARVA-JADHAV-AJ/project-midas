with open("frontend/components/file_viewer.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
code = re.sub(r'st\.subheader\(.*?\)', 'st.subheader("Generated Outputs")', code)

with open("frontend/components/file_viewer.py", "w", encoding="utf-8") as f:
    f.write(code)
