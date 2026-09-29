with open('requirements.txt', 'rb') as f:
    content = f.read()
# Replace null bytes
content = content.replace(b'\x00', b'')
with open('requirements.txt', 'wb') as f:
    f.write(content)
