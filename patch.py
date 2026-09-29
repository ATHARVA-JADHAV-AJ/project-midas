import re

with open("frontend/app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Make it automatically authenticated
code = code.replace('st.session_state.token = None', 'st.session_state.token = "bypass"')

# Remove the sidebar auth entirely
code = re.sub(r'# --- Sidebar Auth ---.*?# --- Hero Section ---', '# --- Hero Section ---', code, flags=re.DOTALL)

# Remove the token arg from render_thought_stream
code = code.replace('def render_thought_stream(task_id: str, token: str):', 'def render_thought_stream(task_id: str, token: str = "bypass"):')

with open("frontend/app.py", "w", encoding="utf-8") as f:
    f.write(code)
