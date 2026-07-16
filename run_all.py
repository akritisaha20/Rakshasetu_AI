"""
run_all.py
RakshaSetu AI - Combined Demo Runner

Runs Modules 1, 2, 3, and 4 ALL TOGETHER in a single process / single
terminal window -- for demo purposes, so you don't need to juggle
multiple terminals. Module 5 (the dashboard) is still a separate
browser tab, since in the real system that's a genuinely different
device (a family member's phone/laptop).

Place this file at the TOP LEVEL of your Raksha_AI folder, alongside
Module_1, Module_2, Module_3, Module_4 (NOT inside any of them).

Run with:
    python run_all.py
"""

import sys
import os
import time
import threading
from flask import Flask, jsonify

# Make all 4 module folders importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for module_folder in ["Module_1", "Module_2", "Module_3", "Module_4"]:
    sys.path.insert(0, os.path.join(BASE_DIR, module_folder))

from camera_dev import RakshaCamera          # noqa: E402  (Module 1 - laptop webcam)
from pose_detector import PoseDetector       # noqa: E402
from hand_detector import HandDetector       # noqa: E402
from face_detector import FaceDetector       # noqa: E402
from hazard_detector import HazardDetector   # noqa: E402
from json_output import build_output         # noqa: E402

from mode_manager import ModeManager         # noqa: E402  (Module 2)

from hardware_bridge import HardwareBridge   # noqa: E402  (Module 3)

from cloud_backend import CloudBackend       # noqa: E402  (Module 4)


TARGET_FPS = 15
FRAME_INTERVAL = 1.0 / TARGET_FPS
DASHBOARD_PORT = 5001
DEMO_LEFT_PWM = 60
DEMO_RIGHT_PWM = 60

# Performance tuning for slower hardware (e.g. Raspberry Pi):
# YOLO hazard detection is the most expensive step -- only run it
# every Nth frame and reuse the last result in between. Hazards on
# the floor don't change fast enough to need checking every frame.
HAZARD_CHECK_EVERY_N_FRAMES = 3

app = Flask(__name__)
backend = CloudBackend(caregiver_phone="+15551234567", robot_name="Raksha AI Robot")
latest_status = {}


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(latest_status)


@app.route("/digital_twin", methods=["GET"])
def get_digital_twin():
    try:
        import json
        twin_path = os.path.join(BASE_DIR, "Module_4", "digital_twin.json")
        with open(twin_path) as f:
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
    app.run(host="0.0.0.0", port=DASHBOARD_PORT, debug=False, use_reloader=False)


def main():
    global latest_status

    print("=" * 60)
    print("RakshaSetu AI - Combined Demo Runner")
    print("All 4 backend modules running together in this one window.")
    print("=" * 60)

    cam = RakshaCamera().start()
    pose_detector = PoseDetector()
    hand_detector = HandDetector()
    face_detector = FaceDetector()
    hazard_detector = HazardDetector()

    hw = HardwareBridge()

    def on_state_change(old_state, new_state, data):
        if new_state == "SAFETY_ALERT":
            backend.dispatch_emergency_alert(reason="mode_manager_escalation")

    manager = ModeManager(
        on_state_change=on_state_change,
        on_verification_prompt=hw.speak,
    )

    server_thread = threading.Thread(target=run_dashboard_server, daemon=True)
    server_thread.start()

    print(f"\nDashboard should point to: http://localhost:{DASHBOARD_PORT}/digital_twin")
    print("Open Module_5/dashboard.html in your browser now.\n")
    print("Starting camera loop... (Ctrl+C to stop)\n")

    last_state = None
    last_accessibility_mode = None
    frame_count = 0
    cached_hazard_in_path = False
    cached_hazard_type = None
    fps_counter = 0
    fps_timer_start = time.time()

    try:
        while True:
            loop_start = time.time()
            frame = cam.get_frame()
            frame_count += 1

            fall_suspected = pose_detector.process(frame)
            gesture = hand_detector.process(frame)
            pain_index = face_detector.process(frame)

            # Only run the expensive YOLO hazard check every Nth frame;
            # reuse the last result on skipped frames.
            if frame_count % HAZARD_CHECK_EVERY_N_FRAMES == 0:
                cached_hazard_in_path, cached_hazard_type = hazard_detector.process(frame)
            hazard_in_path = cached_hazard_in_path
            hazard_type = cached_hazard_type

            output = build_output(
                fall_suspected=fall_suspected,
                detected_gesture=gesture,
                pain_index=pain_index,
                hazard_in_path=hazard_in_path,
                hazard_type=hazard_type,
            )
            latest_status = output

            manager.process_telemetry(output)

            backend.log_telemetry(output, robot_state=manager.current_state)
            backend.sync_digital_twin(
                output, robot_state=manager.current_state,
                accessibility_mode=manager.accessibility_mode
            )

            if (manager.current_state != last_state or
                    manager.accessibility_mode != last_accessibility_mode):
                hw.enforce_hardware_profile(
                    manager.current_state,
                    accessibility_mode=manager.accessibility_mode,
                    raw_left_pwm=DEMO_LEFT_PWM,
                    raw_right_pwm=DEMO_RIGHT_PWM,
                )
                last_state = manager.current_state
                last_accessibility_mode = manager.accessibility_mode

            elapsed = time.time() - loop_start
            sleep_time = FRAME_INTERVAL - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

            # Measure and print the REAL achieved FPS every 3 seconds,
            # so you can verify whether tuning changes actually helped.
            fps_counter += 1
            if time.time() - fps_timer_start >= 3.0:
                actual_fps = fps_counter / (time.time() - fps_timer_start)
                print(f"[Performance] Actual FPS: {actual_fps:.1f} (target: {TARGET_FPS})")
                fps_counter = 0
                fps_timer_start = time.time()

    except KeyboardInterrupt:
        print("\nStopping RakshaSetu AI...")
    finally:
        cam.stop()
        pose_detector.close()
        hand_detector.close()
        face_detector.close()
        hw.close()


if __name__ == "__main__":
    main()
