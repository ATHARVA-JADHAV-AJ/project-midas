with open("sandbox/restricted_runner.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.strip() == "if exec_exception:":
        skip = True
        new_lines.append("    if exec_exception:\n")
        new_lines.append("        exc = exec_exception[0]\n")
        new_lines.append("        result['exit_code'] = 1\n")
        new_lines.append("        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)\n")
        new_lines.append("        filtered_tb = [ln for ln in tb_lines if '/app/sandbox/restricted_runner.py' not in ln]\n")
        new_lines.append("        result['stderr'] = ''.join(filtered_tb)\n")
        continue
    if skip:
        if line.strip() == "else:":
            skip = False
            new_lines.append("    else:\n")
        continue
    new_lines.append(line)

with open("sandbox/restricted_runner.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
