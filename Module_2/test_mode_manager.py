"""
test_mode_manager.py
Standalone test for the ModeManager -- uses FAKE/simulated telemetry data,
so you can verify the decision logic works correctly WITHOUT needing
Module 1's camera running. Run this first before connecting to real data.
"""

import time
from mode_manager import ModeManager

manager = ModeManager()

print("=== TEST 1: Normal operation (should stay CONVERSATION) ===")
manager.process_telemetry({
    "fall_suspected": False, "detected_gesture": None,
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
time.sleep(0.5)

print("\n=== TEST 2: Hazard appears (should switch to ACCESSIBILITY) ===")
manager.process_telemetry({
    "fall_suspected": False, "detected_gesture": None,
    "pain_index": 0, "hazard_in_path": True, "hazard_type": "backpack"
})
time.sleep(0.5)

print("\n=== TEST 3: Hazard clears (should switch back to CONVERSATION) ===")
manager.process_telemetry({
    "fall_suspected": False, "detected_gesture": None,
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
time.sleep(0.5)

print("\n=== TEST 3b: Wave gesture (should switch to ACCESSIBILITY / Hearing-Impaired) ===")
manager.process_telemetry({
    "fall_suspected": False, "detected_gesture": "Wave",
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
time.sleep(0.5)

print("\n=== TEST 3c: Wave stops (should switch back to CONVERSATION) ===")
manager.process_telemetry({
    "fall_suspected": False, "detected_gesture": None,
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
time.sleep(0.5)

print("\n=== TEST 4: Fall detected, then Thumbs_Up within window (false alarm dismissed) ===")
manager.process_telemetry({
    "fall_suspected": True, "detected_gesture": None,
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
time.sleep(1)
manager.process_telemetry({
    "fall_suspected": False, "detected_gesture": "Thumbs_Up",
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
time.sleep(0.5)

print("\n=== TEST 5: Fall detected, NO confirmation within window (should escalate) ===")
manager.process_telemetry({
    "fall_suspected": True, "detected_gesture": None,
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})
print("(waiting 6 seconds to simulate no response...)")
time.sleep(6)
manager.process_telemetry({
    "fall_suspected": False, "detected_gesture": None,
    "pain_index": 0, "hazard_in_path": False, "hazard_type": None
})

print("\n=== TEST 6: Manually clearing the safety alert ===")
manager.reset_safety_alert()

print("\n=== TEST 7: Sustained high pain_index (should escalate after ~3 seconds) ===")
for i in range(5):
    manager.process_telemetry({
        "fall_suspected": False, "detected_gesture": None,
        "pain_index": 8, "hazard_in_path": False, "hazard_type": None
    })
    time.sleep(1)

print("\nAll tests complete. Review the printed state changes above.")
