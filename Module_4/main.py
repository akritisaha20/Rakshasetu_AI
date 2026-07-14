"""
main.py
Module 4: Combined runner.

Connects the full pipeline:
  Module 1 (camera, over HTTP) -> Module 2 (ModeManager decisions)
  -> Module 4 (CloudBackend: logging, digital twin sync, emergency alerts)

Also runs its own small HTTP server (port 5001) so Module 5's web
dashboard can fetch the live digital twin + recent logs from a browser.

Requires Module 1's main.py to already be running (so
http://localhost:5000/status is live) before you start this script.
"""

import sys
import os
import time
import threading
import requests
from flask import Flask, jsonify

# Import Module 2's ModeManager from the sibling Module_2 folder
MODULE_2_PATH = os.path.join(os.path.dirname(__file__), "..", "Module_2")
sys.path.insert(0, MODULE_2_PATH)
from mode_manager import ModeManager  # noqa: E402

from cloud_backend import CloudBackend

MODULE_1_URL = "http://localhost:5000/status"
POLL_INTERVAL = 1.0 / 15  # match Module 1's ~15 FPS refresh rate
HEARTBEAT_CHECK_INTERVAL = 5.0  # how often to check the watchdog
DASHBOARD_SERVER_PORT = 5001

app = Flask(__name__)
backend = CloudBackend(caregiver_phone="+15551234567", robot_name="Raksha AI Robot")


@app.after_request
def add_cors_headers(response):
    # Allows Module 5's dashboard (opened as a local HTML file / different
    # origin) to fetch this data directly from the browser.
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/digital_twin", methods=["GET"])
def get_digital_twin():
    try:
        import json
        with open(os.path.join(os.path.dirname(__file__), "digital_twin.json")) as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify({"error": "No data yet"}), 404


@app.route("/logs", methods=["GET"])
def get_logs():
    rows = backend.get_recent_logs(limit=20)
    logs = [
        {
            "timestamp": r[0], "fall_suspected": bool(r[1]), "detected_gesture": r[2],
            "pain_index": r[3], "hazard_in_path": bool(r[4]), "hazard_type": r[5],
            "robot_state": r[6],
        }
        for r in rows
    ]
    return jsonify(logs)


def run_dashboard_server():
    app.run(host="0.0.0.0", port=DASHBOARD_SERVER_PORT, debug=False, use_reloader=False)


def main():
    def on_state_change(old_state, new_state, data):
        if new_state == "SAFETY_ALERT":
            backend.dispatch_emergency_alert(reason="mode_manager_escalation")

    manager = ModeManager(on_state_change=on_state_change)

    server_thread = threading.Thread(target=run_dashboard_server, daemon=True)
    server_thread.start()

    print(f"Module 4 started. Polling Module 1 at {MODULE_1_URL} ...")
    print(f"Dashboard data available at http://localhost:{DASHBOARD_SERVER_PORT}/digital_twin")
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
