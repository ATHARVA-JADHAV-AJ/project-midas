# Project Midas — Thought Stream Component
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
import streamlit as st
import asyncio
import websockets
import json

import os

async def connect_to_stream(task_id: str, token: str):
    api_url = os.getenv("API_URL", "http://localhost:8000")
    ws_url = api_url.replace("http://", "ws://").replace("https://", "wss://")
    uri = f"{ws_url}/ws/{task_id}?token={token}"
    try:
        async with websockets.connect(uri) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                
                # Append to session state
                if "thoughts" not in st.session_state:
                    st.session_state.thoughts = []
                
                st.session_state.thoughts.append(data)
                
                if data["event_type"] in ["result", "error"]:
                    break
    except Exception as e:
        st.session_state.thoughts.append({"event_type": "error", "payload": f"Stream error: {e}"})

def render_thought_stream(task_id: str, token: str):
    st.subheader("🧠 Agentic Thought Stream")
    
    if task_id:
        st.markdown(f"**Tracking Task:** `{task_id}`")
        
        # Async runner for websocket
        if st.button("Connect to Stream"):
            st.session_state.thoughts = []
            with st.spinner("Listening to agent thoughts..."):
                asyncio.run(connect_to_stream(task_id, token))
                st.rerun()

    # Display thoughts
    if "thoughts" in st.session_state and st.session_state.thoughts:
        for t in st.session_state.thoughts:
            event = t.get("event_type", "thought")
            payload = t.get("payload", "")
            
            if event == "thought":
                st.info(f"💭 {payload}")
            elif event == "status":
                st.warning(f"⚡ {payload}")
            elif event == "result":
                st.success(f"✅ {payload}")
            elif event == "error":
                st.error(f"❌ {payload}")
    else:
        st.caption("No thoughts recorded yet.")
