with open("api/router.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "{prompt}":
        continue
    new_lines.append(line)

with open("api/router.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
