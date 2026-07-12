"""
main.py
Module 2: Connects to Module 1's live HTTP endpoint (/status) and feeds
each new reading into the ModeManager in real time.

Requires Module 1's main.py to already be running (so http://localhost:5000/status
is live) before you start this script.
"""

import time
import requests

from mode_manager import ModeManager

MODULE_1_URL = "http://localhost:5000/status"
POLL_INTERVAL = 1.0 / 15  # match Module 1's ~15 FPS refresh rate


def main():
    manager = ModeManager()
    print(f"Module 2 started. Polling Module 1 at {MODULE_1_URL} ...")
    print(f"Current state: {manager.current_state}\n")

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

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping Module 2...")
