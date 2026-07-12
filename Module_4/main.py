"""
main.py
Module 4: Combined runner.

Connects the full pipeline:
  Module 1 (camera, over HTTP) -> Module 2 (ModeManager decisions)
  -> Module 4 (CloudBackend: logging, digital twin sync, emergency alerts)

Requires Module 1's main.py to already be running (so
http://localhost:5000/status is live) before you start this script.
"""

import sys
import os
import time
import requests

# Import Module 2's ModeManager from the sibling Module_2 folder
MODULE_2_PATH = os.path.join(os.path.dirname(__file__), "..", "Module_2")
sys.path.insert(0, MODULE_2_PATH)
from mode_manager import ModeManager  # noqa: E402

from cloud_backend import CloudBackend

MODULE_1_URL = "http://localhost:5000/status"
POLL_INTERVAL = 1.0 / 15  # match Module 1's ~15 FPS refresh rate
HEARTBEAT_CHECK_INTERVAL = 5.0  # how often to check the watchdog


def main():
    backend = CloudBackend(caregiver_phone="+15551234567", robot_name="Raksha AI Robot")

    def on_state_change(old_state, new_state, data):
        if new_state == "SAFETY_ALERT":
            backend.dispatch_emergency_alert(reason="mode_manager_escalation")

    manager = ModeManager(on_state_change=on_state_change)

    print(f"Module 4 started. Polling Module 1 at {MODULE_1_URL} ...")
    print(f"Current state: {manager.current_state}\n")

    last_heartbeat_check = time.time()

    while True:
        try:
            response = requests.get(MODULE_1_URL, timeout=1)
            data = response.json()
            manager.process_telemetry(data)

            # Log every reading to the real local database
            backend.log_telemetry(data, robot_state=manager.current_state)

            # Keep the digital twin (simulated Firebase) up to date
            backend.sync_digital_twin(
                data, robot_state=manager.current_state,
                accessibility_mode=manager.accessibility_mode
            )

        except requests.exceptions.ConnectionError:
            print("Could not reach Module 1. Is main.py running in the other terminal?")
            time.sleep(2)
            continue
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(1)
            continue

        # Periodic watchdog check
        if time.time() - last_heartbeat_check >= HEARTBEAT_CHECK_INTERVAL:
            backend.check_heartbeat()
            last_heartbeat_check = time.time()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping Module 4...")
