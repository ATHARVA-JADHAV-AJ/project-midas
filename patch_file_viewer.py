import re

with open("frontend/components/file_viewer.py", "r", encoding="utf-8") as f:
    code = f.read()

replacement = """def render_file_viewer():
    if not OUTPUTS_DIR.exists():
        st.info("Outputs directory is empty.")
        return
        
    all_files = [f for f in OUTPUTS_DIR.glob("*") if f.is_file()]
    if not all_files:
        st.info("No generated files yet.")
        return
        
    # Sort files by modification time, newest first
    all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    import time
    current_time = time.time()
    
    # Files created/modified in the last 60 seconds are considered "Current"
    current_files = [f for f in all_files if (current_time - f.stat().st_mtime) <= 60]
    previous_files = [f for f in all_files if (current_time - f.stat().st_mtime) > 60]
    
    if current_files:
        for file_path in current_files:
            with st.expander(f"New: {file_path.name}", expanded=True):
                ext = file_path.suffix.lower()
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"Download {file_path.name}",
                        data=f,
                        file_name=file_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if ext == ".xlsx" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_new_{file_path.name}"
                    )
                if ext == ".xlsx":
                    try:
                        df = pd.read_excel(file_path)
                        st.dataframe(df.head(10))
                        if len(df) > 10:
                            st.caption(f"Showing first 10 rows (Total: {len(df)})")
                    except Exception as e:
                        st.warning(f"Could not preview spreadsheet: {e}")
                elif ext == ".docx":
                    st.caption("Word document preview is not natively supported. Please download to view.")
                    
    st.markdown("---")
    st.subheader("Previously Downloadable Files")
    if previous_files:
        for file_path in previous_files:
            with st.expander(f"{file_path.name}"):
                ext = file_path.suffix.lower()
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"Download {file_path.name}",
                        data=f,
                        file_name=file_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if ext == ".xlsx" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_old_{file_path.name}"
                    )
    else:
        st.caption("No previous files.")"""

code = re.sub(r'def render_file_viewer\(\):.*', replacement, code, flags=re.DOTALL)

with open("frontend/components/file_viewer.py", "w", encoding="utf-8") as f:
    f.write(code)
