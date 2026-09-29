import re

with open("core/nodes/reasoner.py", "r", encoding="utf-8") as f:
    code = f.read()

patch = """    # Extract file path from prompt
    import base64
    image_base64 = None
    match = re.search(r"\[File Attached: (.*?)\]", state['prompt'])
    if match:
        file_path = match.group(1)
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                with open(file_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to load image {file_path}: {e}")

    client = ollama.Client(host=OLLAMA_URL)
    try:
        msg = {
            "role": "user",
            "content": (
                "Extract all structured data, tables, and key information from this image. "
                f"Task context: {state['prompt']}"
            )
        }
        if image_base64:
            msg["images"] = [image_base64]
            
        response = client.chat(
            model=MODEL_VISION,
            messages=[msg],"""

code = re.sub(r'    client = ollama\.Client\(host=OLLAMA_URL\)\n    try:\n        response = client\.chat\(\n            model=MODEL_VISION,\n            messages=\[\{\n                "role": "user",\n                "content": \(\n                    "Extract all structured data, tables, and key information from this image\. "\n                    f"Task context: \{state\[\'prompt\'\]\}"\n                \),\n            \}\],', patch, code)

with open("core/nodes/reasoner.py", "w", encoding="utf-8") as f:
    f.write(code)
