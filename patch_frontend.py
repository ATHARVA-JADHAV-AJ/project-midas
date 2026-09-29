import re

with open("frontend/app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace the polling logic in tab1
polling_replacement = """        if res.status_code == 200:
            task_data = res.json()
            status = task_data['status']
            
            if status not in ["done", "failed", "waiting_approval"]:
                with st.spinner(f"Agent {status.upper()}... Please wait."):
                    import time
                    while status not in ["done", "failed", "waiting_approval"]:
                        time.sleep(1.0)
                        res = requests.get(f"{API_URL}/tasks/{st.session_state.current_task_id}", headers=headers)
                        if res.status_code == 200:
                            task_data = res.json()
                            status = task_data['status']
                        else:
                            break
            
            if status == "done":
                st.success("Task Complete")
                if task_data.get("output_path"):
                    st.info(f"Artifact Generated: {task_data['output_path']}")
                st.markdown("**Final Report:**")
                st.write(task_data.get("result", ""))
                st.markdown("---")
                render_file_viewer()
            elif status == "failed":
                st.error(f"Execution Failed: {task_data.get('error', 'Unknown Error')}")
            elif status == "waiting_approval":
                st.warning("**Approval Hold:** Your task requires Command Center clearance to proceed. Please contact your administrator.")"""

code = re.sub(r'        if res\.status_code == 200:\n            task_data = res\.json\(\)\n            status = task_data\[\'status\'\]\n.*?(?=# -------------------------------------------------------------)', polling_replacement + "\n\n", code, flags=re.DOTALL)

# Remove render_file_viewer from tab2
code = re.sub(r'        with col_right:\n            st\.markdown\("#### Sandbox Output Viewer"\)\n            render_file_viewer\(\)', '', code, flags=re.DOTALL)

with open("frontend/app.py", "w", encoding="utf-8") as f:
    f.write(code)
