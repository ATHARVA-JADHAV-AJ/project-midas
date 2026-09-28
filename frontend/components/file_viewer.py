# Project Midas Ã¢â‚¬â€ File Viewer Component
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
import streamlit as st
import os
import pandas as pd
from pathlib import Path

OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", "./outputs"))

def render_file_viewer():
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
                mime = "application/octet-stream"
                if ext == ".xlsx": mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif ext == ".docx": mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif ext == ".pptx": mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                elif ext == ".pdf": mime = "application/pdf"
                elif ext == ".svg": mime = "image/svg+xml"
                
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"Download {file_path.name}",
                        data=f,
                        file_name=file_path.name,
                        mime=mime,
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
                elif ext == ".pdf":
                    st.caption("PDF preview is not natively supported. Please download to view.")
                elif ext == ".pptx":
                    st.caption("PowerPoint preview is not natively supported. Please download to view.")
                elif ext == ".svg":
                    st.image(file_path, caption=file_path.name)
                    
    st.markdown("---")
    st.subheader("Previously Downloadable Files")
    if previous_files:
        for file_path in previous_files:
            with st.expander(f"{file_path.name}"):
                ext = file_path.suffix.lower()
                mime = "application/octet-stream"
                if ext == ".xlsx": mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif ext == ".docx": mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif ext == ".pptx": mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                elif ext == ".pdf": mime = "application/pdf"
                elif ext == ".svg": mime = "image/svg+xml"
                
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"Download {file_path.name}",
                        data=f,
                        file_name=file_path.name,
                        mime=mime,
                        key=f"dl_old_{file_path.name}"
                    )
    else:
        st.caption("No previous files.")