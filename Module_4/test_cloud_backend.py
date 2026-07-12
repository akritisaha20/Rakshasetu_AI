"""
test_cloud_backend.py
Standalone test for the CloudBackend -- uses FAKE/simulated telemetry,
so you can verify the logging and alert logic works correctly WITHOUT
needing a real Firebase project or Twilio account.
"""

import time
from cloud_backend import CloudBackend

backend = CloudBackend(caregiver_phone="+15551234567", robot_name="Raksha Test Bot")

print("\n=== TEST 1: Normal telemetry sync ===")
data = {"timestamp": int(time.time()), "fall_suspected": False,
        "detected_gesture": None, "pain_index": 0,
        "hazard_in_path": False, "hazard_type": None}
backend.log_telemetry(data, robot_state="CONVERSATION")
twin = backend.sync_digital_twin(data, robot_state="CONVERSATION")
print(f"Digital twin written: {twin}")

print("\n=== TEST 2: Vision-Impaired accessibility sync ===")
data = {"timestamp": int(time.time()), "fall_suspected": False,
        "detected_gesture": None, "pain_index": 0,
        "hazard_in_path": True, "hazard_type": "backpack"}
backend.log_telemetry(data, robot_state="ACCESSIBILITY")
twin = backend.sync_digital_twin(data, robot_state="ACCESSIBILITY", accessibility_mode="VISION_IMPAIRED")
print(f"Digital twin written: {twin}")

print("\n=== TEST 3: Emergency! Fall confirmed, dispatch alert ===")
data = {"timestamp": int(time.time()), "fall_suspected": True,
        "detected_gesture": None, "pain_index": 2,
        "hazard_in_path": False, "hazard_type": None}
backend.log_telemetry(data, robot_state="SAFETY_ALERT")
backend.sync_digital_twin(data, robot_state="SAFETY_ALERT")
backend.dispatch_emergency_alert(reason="no_response_after_fall")

print("\n=== TEST 4: Heartbeat check (should be healthy, just synced) ===")
is_healthy = backend.check_heartbeat()
print(f"Heartbeat healthy: {is_healthy}")

print("\n=== TEST 5: Reading back recent logs from the REAL local database ===")
logs = backend.get_recent_logs(limit=5)
for row in logs:
    print(f"  {row}")

print(f"\nAll tests complete. Check '{backend.__class__.__module__}' folder for:")
print("  - raksha_local_logs.db  (real SQLite database file)")
print("  - digital_twin.json     (simulated Firebase sync file)")
