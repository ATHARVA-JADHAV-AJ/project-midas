with open("sandbox/restricted_runner.py", "r", encoding="utf-8") as f:
    code = f.read()

import re
replacement = """    if exec_exception:
        exc = exec_exception[0]
        result["exit_code"] = 1
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        filtered_tb = [line for line in tb_lines if "/app/sandbox/restricted_runner.py" not in line]
        result["stderr"] = "".join(filtered_tb)
    else:"""

code = re.sub(r'    if exec_exception:.*?else:', replacement, code, flags=re.DOTALL)

with open("sandbox/restricted_runner.py", "w", encoding="utf-8") as f:
    f.write(code)
