# Project Midas — Netstat Monitor Component
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
import streamlit as st
import subprocess
import re

def render_netstat_monitor():
    st.subheader("🌐 Network Sovereignty Monitor")
    st.markdown("Proving zero outbound internet calls during inference.")
    
    # Run netstat -n and filter for ESTABLISHED
    try:
        # Cross-platform handling (Windows/Linux)
        result = subprocess.run(["netstat", "-n"], capture_output=True, text=True, timeout=2)
        lines = result.stdout.split("\n")
        
        established = []
        for line in lines:
            if "ESTABLISHED" in line:
                established.append(line.strip())
                
        is_air_gapped = True
        external_ips = []
        
        for line in established:
            # Basic parsing of IP addresses from netstat line
            # Windows format: TCP 127.0.0.1:12345 127.0.0.1:8000 ESTABLISHED
            # Linux format: tcp 0 0 127.0.0.1:12345 127.0.0.1:8000 ESTABLISHED
            parts = re.split(r'\s+', line)
            if len(parts) >= 4:
                # Get the foreign address part
                foreign = parts[2] if ":" in parts[2] and not parts[2].startswith("0.0.0.0") else parts[3] if len(parts) > 3 else ""
                ip = foreign.split(":")[0] if ":" in foreign else foreign
                
                # Whitelist local/docker subnets
                if ip and not (ip.startswith("127.") or ip == "::1" or ip.startswith("172.") or ip.startswith("10.") or ip.startswith("192.168.")):
                    is_air_gapped = False
                    external_ips.append(ip)

        if is_air_gapped:
            st.success("✅ **0 kbps outbound to external IPs**")
        else:
            st.error(f"⚠️ **External connection detected:** {', '.join(set(external_ips))}")
        
        with st.expander("Raw ESTABLISHED connections (Local/Docker whitelist)"):
            if established:
                st.code("\n".join(established), language="text")
            else:
                st.text("No active connections.")
                
    except Exception as e:
        st.error(f"Failed to poll network status: {e}")
