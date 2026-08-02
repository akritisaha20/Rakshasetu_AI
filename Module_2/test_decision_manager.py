"""
test_decision_manager.py
Demonstrates all 5 engines working together, with fake data --
no camera or real hardware needed.
"""

import time
from decision_manager import DecisionManager

manager = DecisionManager()

print("=" * 60)
print("TEST 1: Memory Engine -- teaching it a new fact")
print("=" * 60)
result = manager.memory.extract_and_remember("My daughter Neha visits every Sunday")
print(f"Extraction result: {result}")
print(f"Stored family members: {manager.memory.get_family_members()}")

print("\n" + "=" * 60)
print("TEST 2: Companion Engine -- using that memory in conversation")
print("=" * 60)
response = manager.handle_conversation("I miss my daughter")
print(f"User: I miss my daughter")
print(f"Robot: {response}")

print("\n" + "=" * 60)
print("TEST 3: Companion Engine -- medication reminder")
print("=" * 60)
manager.memory.remember_medication("Metformin", "8:00 AM and 8:00 PM")
response = manager.handle_conversation("What's my medicine schedule?")
print(f"User: What's my medicine schedule?")
print(f"Robot: {response}")

print("\n" + "=" * 60)
print("TEST 4: Accessibility Profile -- setting and reading adapted settings")
print("=" * 60)
manager.accessibility_profile.set_need("hearing_impaired", True)
settings = manager.get_accessibility_settings()
print(f"Adapted settings for hearing-impaired user: {settings}")

print("\n" + "=" * 60)
print("TEST 5: Safety Engine priority -- conversation blocked during a fall")
print("=" * 60)
manager.process_telemetry({
    "fall_suspected": True, "detected_gesture": None,
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
response = manager.handle_conversation("Hello!")
print(f"(Fall just detected, double-verification active)")
print(f"User: Hello!")
print(f"Robot: {response}")
print(f"Current priority: {manager.get_current_priority()}")

print("\n" + "=" * 60)
print("TEST 6: Clearing the fall with Thumbs_Up, conversation resumes")
print("=" * 60)
manager.process_telemetry({
    "fall_suspected": False, "detected_gesture": "Thumbs_Up",
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
response = manager.handle_conversation("Hello!")
print(f"User: Hello!")
print(f"Robot: {response}")
print(f"Current priority: {manager.get_current_priority()}")

print("\n" + "=" * 60)
print("TEST 7: Wellness Engine -- seeding fake history, then checking today")
print("=" * 60)
import sqlite3
import os
conn = sqlite3.connect(manager.wellness.__class__.__module__ and
                        os.path.join(os.path.dirname(__file__), "wellness.db"))
# Seed 7 days of "normal" activity (~1200 seconds/day) for baseline
for i in range(7):
    fake_date = f"2026-01-0{i+1}"
    conn.execute(
        "INSERT OR REPLACE INTO daily_activity (date, active_seconds) VALUES (?, ?)",
        (fake_date, 1200)
    )
conn.commit()
conn.close()

manager.wellness._today_active_seconds = 200  # today: much lower than baseline
is_anomaly, today, baseline = manager.check_wellness()
print(f"Today's activity: {today}s, Baseline: {baseline}s, Anomaly flagged: {is_anomaly}")
print(f"Current priority after wellness check: {manager.get_current_priority()}")

print("\nAll tests complete.")
