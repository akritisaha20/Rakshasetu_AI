"""
app.py — Streamlit demo for RakshaSetu AI's Decision Layer (Module 2).

This does NOT use a camera. It lets you manually simulate the telemetry
that Module 1 would normally send (fall_suspected, pain_index,
detected_gesture, hazard_in_path) using sliders/buttons, and shows how
the real ModeManager (Module_2/mode_manager.py) reacts in real time.
"""

import sys
import os
import time
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), "Module_2"))
from mode_manager import ModeManager, RobotState, AccessibilityMode  # noqa: E402

st.set_page_config(page_title="RakshaSetu AI — Decision Layer Demo", layout="centered")

if "log" not in st.session_state:
    st.session_state.log = []

if "manager" not in st.session_state:

    def on_state_change(old, new, data):
        st.session_state.log.insert(0, f"🔄 State change: **{old} → {new}**")

    def on_verification_prompt(message):
        st.session_state.log.insert(0, f"🗣️ Robot says: \"{message}\"")

    st.session_state.manager = ModeManager(
        on_state_change=on_state_change,
        on_verification_prompt=on_verification_prompt,
    )

manager = st.session_state.manager

st.title("🤖 RakshaSetu AI — Decision Layer Demo")
st.caption(
    "This simulates Module 1's camera telemetry so you can test the real "
    "Mode Manager (Module 2) without a physical camera — perfect for a "
    "browser demo on Streamlit Cloud."
)

st.divider()

state_colors = {
    RobotState.CONVERSATION: "🟢",
    RobotState.ACCESSIBILITY: "🟡",
    RobotState.SAFETY_ALERT: "🔴",
}
icon = state_colors.get(manager.current_state, "⚪")
sub = f" ({manager.accessibility_mode})" if manager.accessibility_mode else ""
st.subheader(f"{icon} Current State: {manager.current_state}{sub}")

if manager.double_verify_active:
    st.warning("⏳ Waiting for Thumbs-Up confirmation (Double-Verification loop active)...")

st.divider()

st.subheader("Simulate Module 1 Telemetry")

col1, col2 = st.columns(2)
with col1:
    fall_suspected = st.checkbox("Fall suspected")
    hazard_in_path = st.checkbox("Hazard in path")
with col2:
    pain_index = st.slider("Pain index", 0, 10, 0)
    hazard_type = st.selectbox(
        "Hazard type", [None, "backpack", "handbag"], disabled=not hazard_in_path
    )

detected_gesture = st.selectbox(
    "Detected gesture", [None, "Thumbs_Up", "Thumbs_Down", "Wave"]
)

send_col, reset_col = st.columns(2)
with send_col:
    if st.button("📡 Send telemetry frame", use_container_width=True):
        frame = {
            "timestamp": time.time(),
            "fall_suspected": fall_suspected,
            "detected_gesture": detected_gesture,
            "pain_index": pain_index,
            "hazard_in_path": hazard_in_path,
            "hazard_type": hazard_type,
        }
        manager.process_telemetry(frame)
        st.rerun()

with reset_col:
    if st.button("🔁 Manually clear Safety Alert", use_container_width=True):
        manager.reset_safety_alert()
        st.session_state.log.insert(0, "✅ Safety alert manually reset by caregiver.")
        st.rerun()

st.divider()

st.subheader("Event Log")
if st.session_state.log:
    for entry in st.session_state.log[:15]:
        st.write(entry)
else:
    st.write("No events yet — send a telemetry frame above to get started.")
