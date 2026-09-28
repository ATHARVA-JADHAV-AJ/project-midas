import sys
import codecs

f = sys.argv[1]
with open(f, "rb") as file:
    content = file.read()
if content.startswith(codecs.BOM_UTF8):
    content = content[len(codecs.BOM_UTF8):]
    with open(f, "wb") as file:
        file.write(content)
