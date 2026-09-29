import re

with open("core/nodes/reasoner.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

# Add the import stripper hack
patch = """    # Hack for 0.5b model: Strip out import statements because RestrictedPython blocks them
    # and they are already preloaded in the sandbox
    code = re.sub(r"^import .*$|^from .* import .*$", "", code, flags=re.MULTILINE)

    return {"""

code = code.replace("    return {", patch)

with open("core/nodes/reasoner.py", "w", encoding="utf-8") as f:
    f.write(code)
