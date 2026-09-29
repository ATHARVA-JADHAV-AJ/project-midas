with open("docker-compose.yml", "r", encoding="utf-8") as f:
    code = f.read()

# Add sandbox to volumes for celery_worker
import re
code = re.sub(r'(\s+- ./task_queue:/app/task_queue)', r'\1\n      - ./sandbox:/app/sandbox', code)

with open("docker-compose.yml", "w", encoding="utf-8") as f:
    f.write(code)
