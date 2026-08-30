"""
app.py — Streamlit demo for RakshaSetu AI's Module 5 (Caregiver Dashboard).

Renders Module_5/dashboard.html directly inside Streamlit. The dashboard
already falls back to demo data gracefully when its backend
(localhost:5001) isn't reachable, so it works as a static showcase here.
Camera/mic buttons use the browser's own webcam/mic (works over HTTPS,
which Streamlit Cloud provides).
"""

import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="RakshaSetu AI — Caregiver Dashboard", layout="wide")

st.title("🏠 RakshaSetu AI — Caregiver Dashboard")
st.caption(
    "This is Module 5's dashboard.html, rendered directly. It shows demo data "
    "since its backend server isn't running here — camera and mic buttons work "
    "using your browser's own webcam/mic."
)

dashboard_path = os.path.join(os.path.dirname(__file__), "Module_5", "dashboard.html")

try:
    with open(dashboard_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=900, scrolling=True)
except FileNotFoundError:
    st.error(
        f"Couldn't find dashboard.html at `{dashboard_path}`. "
        "Make sure Module_5/dashboard.html exists in the repo."
    )
