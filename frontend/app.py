import streamlit as st
import requests
import os
import json
from pathlib import Path
from components.netstat_monitor import render_netstat_monitor
from components.file_viewer import render_file_viewer
from components.thought_stream import render_thought_stream

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="MIDAS DEFENSE AI v5.0", layout="wide", page_icon="???")

# --- Custom CSS for Animation and Corporate Feel ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    @keyframes pulse-glow {
        0% { box-shadow: 0 0 10px rgba(65, 90, 119, 0.2); }
        50% { box-shadow: 0 0 30px rgba(119, 141, 169, 0.6); }
        100% { box-shadow: 0 0 10px rgba(65, 90, 119, 0.2); }
    }
    @keyframes slide-up {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .hero-container {
        background: rgba(13, 27, 42, 0.85);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(119, 141, 169, 0.3);
        animation: slide-up 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        padding: 4rem 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2.5rem;
        position: relative;
        overflow: hidden;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle at center, rgba(119, 141, 169, 0.15) 0%, transparent 60%);
        animation: pulse-glow 8s infinite alternate;
        z-index: -1;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
        background: linear-gradient(90deg, #e0e1dd, #778da9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.25rem;
        font-weight: 300;
        color: #778da9;
        letter-spacing: 1px;
    }
    .company-info {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 12px;
        color: #e0e1dd;
        margin-bottom: 2rem;
        animation: slide-up 1s ease forwards;
    }
    /* Hide the Ctrl+Enter instruction on text areas */
    .stTextArea [data-testid="InputInstructions"] {
        display: none !important;
    }
    /* Modern sleek buttons */
    .stButton>button {
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for auth and tasks
if "token" not in st.session_state:
    st.session_state.token = "bypass"
if "current_task_id" not in st.session_state:
    st.session_state.current_task_id = None

# --- Hero Section ---
st.markdown("""
<div class="hero-container">
    <div class="hero-title">MIDAS DEFENSE AI v5.0</div>
    <div class="hero-subtitle">Sovereign. Air-Gapped. Uncompromising.</div>
</div>
""", unsafe_allow_html=True)

# --- Corporate Info ---
with st.expander("About Midas Systems Corporation", expanded=False):
    st.markdown("""
    <div class="company-info">
        <h3>Mission Statement</h3>
        <p>Midas Systems provides state-of-the-art, fully autonomous agentic workflows designed exclusively for legacy government hardware. Our proprietary architecture ensures 100% data sovereignty with no external API dependencies.</p>
        <hr/>
        <ul>
            <li><strong>Zero-Trust Architecture:</strong> Hardened code sandbox execution.</li>
            <li><strong>Multi-Modal Intelligence:</strong> Seamless integration of vision, reasoning, and data analysis.</li>
            <li><strong>Human-In-The-Loop:</strong> Strict oversight and approval protocols before any destructive execution.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- Main Layout Sections ---
tab1, tab2 = st.tabs(["Field Agent (Low-Spec Client)", "Command Center (Admin / Analyst)"])

# -------------------------------------------------------------
# TAB 1: LOW SPEC CLIENT
# -------------------------------------------------------------
with tab1:
    st.markdown("### Rapid Task Execution")
    st.caption("Designed for ultra-low latency execution on constrained field hardware. Enter your prompt and await the final synthesized output.")
    
    uploaded_file = st.file_uploader("Attach Document or Image (Optional)", type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx"])
    prompt = st.text_area("Request analysis, document drafting, or image processing...", height=100)
    submitted = st.button("Deploy Agent", type="primary")
    
    if submitted and prompt:
        if not st.session_state.token:
            st.error("Authentication required.")
        else:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            try:
                files = None
                data = {"prompt": prompt}
                if uploaded_file is not None:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                
                res = requests.post(f"{API_URL}/tasks", data=data, files=files, headers=headers)
                if res.status_code == 200:
                    st.session_state.current_task_id = res.json()["task_id"]
                    st.success(f"Agent Deployed! Tracking ID: {st.session_state.current_task_id}")
                else:
                    st.error(f"Deployment Failed: {res.text}")
            except Exception as e:
                st.error(f"Network Error: {e}")

    if st.session_state.current_task_id:
        st.markdown("---")
        st.markdown(f"**Tracking Deployment:** {st.session_state.current_task_id}")
            
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        res = requests.get(f"{API_URL}/tasks/{st.session_state.current_task_id}", headers=headers)
        if res.status_code == 200:
            task_data = res.json()
            status = task_data['status']
            
            if status == "done":
                st.success("Task Complete")
                
                with st.chat_message("assistant"):
                    st.write(task_data.get("result", ""))
                    
                    if task_data.get("output_path"):
                        output_file = Path(task_data['output_path'])
                        if output_file.exists():
                            with open(output_file, "rb") as f:
                                st.download_button(
                                    label=f"⬇️ Download {output_file.name}",
                                    data=f,
                                    file_name=output_file.name,
                                    use_container_width=False,
                                    type="primary"
                                )
                            
                            # Auto-preview if it's an image
                            if output_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]:
                                st.image(str(output_file))

                # We can still show previous files in an expander below
                with st.expander("History / Previous Files"):
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
                st.rerun()

# -------------------------------------------------------------
# TAB 2: COMMAND CENTER
# -------------------------------------------------------------
with tab2:
    st.markdown("### Advanced Operations & Oversight")
    
    if not st.session_state.current_task_id:
        st.info("No active task deployed. Deploy a task from the Field Agent tab.")
    else:
        # HITL Approval Gate
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        res = requests.get(f"{API_URL}/tasks/{st.session_state.current_task_id}", headers=headers)
        if res.status_code == 200:
            task_data = res.json()
            if task_data["status"] == "waiting_approval":
                st.error("ACTION REQUIRED: Human-in-the-Loop Override")
                st.markdown("The agent has generated code that requires explicit authorization before sandbox execution.")
                st.code(task_data.get("result", ""), language="python")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Approve & Execute Sandbox", use_container_width=True):
                        approve_res = requests.post(f"{API_URL}/tasks/{st.session_state.current_task_id}/approve", headers=headers)
                        if approve_res.status_code == 200:
                            st.success("Execution Authorized.")
                            st.rerun()
                        else:
                            st.error("Authorization sync failed.")
                with col_b:
                    if st.button("Reject & Terminate", use_container_width=True):
                        reject_res = requests.post(f"{API_URL}/tasks/{st.session_state.current_task_id}/reject", headers=headers)
                        if reject_res.status_code == 200:
                            st.success("Task Terminated.")
                            st.rerun()
                        else:
                            st.error("Termination sync failed.")
                st.divider()

        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("#### Live Thought Stream (Redis)")
            render_thought_stream(st.session_state.current_task_id, st.session_state.token)
            
            st.markdown("#### Network Sovereignty Monitor")
            render_netstat_monitor()
            









