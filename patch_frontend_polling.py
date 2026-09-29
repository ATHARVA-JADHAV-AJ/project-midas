import re

with open("frontend/app.py", "r", encoding="utf-8") as f:
    code = f.read()

replacement = """        if res.status_code == 200:
            task_data = res.json()
            status = task_data['status']
            
            if status == "done":
                st.success("Task Complete")
                if task_data.get("output_path"):
                    st.info(f"Artifact Generated: {task_data['output_path']}")
                st.markdown("**Final Report:**")
                st.write(task_data.get("result", ""))
                st.markdown("---")
                st.markdown("#### Generated Outputs")
                render_file_viewer()
            elif status == "failed":
                st.error(f"Execution Failed: {task_data.get('error', 'Unknown Error')}")
                st.markdown("---")
                st.markdown("#### Generated Outputs")
                render_file_viewer()
            elif status == "waiting_approval":
                st.warning("**Approval Hold:** Your task requires Command Center clearance to proceed. Please contact your administrator.")
            else:
                st.info(f"Status: {status.upper()} (Processing...)")
                import time
                time.sleep(1.0)
                st.rerun()"""

code = re.sub(r'        if res\.status_code == 200:\n            task_data = res\.json\(\)\n            status = task_data\[\'status\'\].*?(?=# -------------------------------------------------------------)', replacement + "\n\n", code, flags=re.DOTALL)

with open("frontend/app.py", "w", encoding="utf-8") as f:
    f.write(code)
