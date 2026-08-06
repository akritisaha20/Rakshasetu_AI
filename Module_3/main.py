"""
main.py
Module 3: Standalone runner (camera + decisions + hardware only,
no cloud logging -- use run_all.py for the full combined system).

Connects the full pipeline together:
  Module 1 (camera, over HTTP) -> Module 2 (DecisionManager, all 5 engines)
  -> Module 3 (HardwareBridge actions)

FIXED: previously imported the old plain ModeManager directly, which
was inconsistent with run_all.py (which uses the full DecisionManager
with all 5 engines). Now both use the same DecisionManager, so
behavior is consistent whether you run Module 3 standalone or as part
of the combined run_all.py.

Requires Module 1's main.py to already be running (so
http://localhost:5000/status is live) before you start this script.
"""

import sys
import os
import time
import requests

# Import Module 2's DecisionManager from the sibling Module_2 folder
MODULE_2_PATH = os.path.join(os.path.dirname(__file__), "..", "Module_2")
sys.path.insert(0, MODULE_2_PATH)
from decision_manager import DecisionManager  # noqa: E402

from hardware_bridge import HardwareBridge

MODULE_1_URL = "http://localhost:5000/status"
POLL_INTERVAL = 1.0 / 15  # match Module 1's ~15 FPS refresh rate

# Example baseline forward-motion speed used when in normal CONVERSATION mode.
# In the real system, this would come from an actual navigation/tracking system.
DEMO_LEFT_PWM = 60
DEMO_RIGHT_PWM = 60


def main():
    hw = HardwareBridge()
    manager = DecisionManager(on_verification_prompt=hw.speak)

    # Demo seed data so Memory/Companion features have something to
    # show immediately when testing Module 3 standalone.
    manager.memory.set_user_name("Aditi")
    if not manager.memory.get_family_members():
        manager.memory.remember_family_member("Neha", "daughter", "every Sunday")

    print(f"Module 3 started. Polling Module 1 at {MODULE_1_URL} ...")
    print(f"Current state: {manager.safety.current_state}\n")

    last_state = None
    last_accessibility_mode = None

    while True:
        try:
            response = requests.get(MODULE_1_URL, timeout=1)
            data = response.json()
            manager.process_telemetry(data)
        except requests.exceptions.ConnectionError:
            print("Could not reach Module 1. Is main.py running in the other terminal?")
            time.sleep(2)
            continue
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(1)
            continue

        # Only push a hardware update when something actually changed,
        # to avoid spamming identical commands 15 times a second.
        if (manager.safety.current_state != last_state or
                manager.safety.accessibility_mode != last_accessibility_mode):
            hw.enforce_hardware_profile(
                manager.safety.current_state,
                accessibility_mode=manager.safety.accessibility_mode,
                raw_left_pwm=DEMO_LEFT_PWM,
                raw_right_pwm=DEMO_RIGHT_PWM,
            )
            last_state = manager.safety.current_state
            last_accessibility_mode = manager.safety.accessibility_mode

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping Module 3...")
