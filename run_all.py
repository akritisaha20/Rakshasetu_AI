"""
run_all.py
RakshaSetu AI - Combined Demo Runner

Runs Modules 1, 2, 3, and 4 ALL TOGETHER in a single process / single
terminal window -- for demo purposes, so you don't need to juggle
multiple terminals. Module 5 (the dashboard) is still a separate
browser tab, since in the real system that's a genuinely different
device (a family member's phone/laptop).

UPDATED: now uses Module 2's DecisionManager (orchestrates Safety +
Accessibility + Memory + Wellness + Companion engines) instead of
ModeManager alone, and exposes /memory, /wellness, and /accessibility
endpoints so the dashboard can show real data instead of demo values.

Place this file at the TOP LEVEL of your Raksha_AI folder, alongside
Module_1, Module_2, Module_3, Module_4 (NOT inside any of them).

Run with:
    python run_all.py
"""

import sys
import os
import time
import threading
from flask import Flask, jsonify, request

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

from decision_manager import DecisionManager, DecisionPriority   # noqa: E402  (Module 2)

from hardware_bridge import HardwareBridge   # noqa: E402  (Module 3)

from cloud_backend import CloudBackend       # noqa: E402  (Module 4)


TARGET_FPS = 15
FRAME_INTERVAL = 1.0 / TARGET_FPS
DASHBOARD_PORT = 5001
DEMO_LEFT_PWM = 60
DEMO_RIGHT_PWM = 60

HAZARD_CHECK_EVERY_N_FRAMES = 3

# How often to run the Wellness Engine's daily anomaly check, in seconds.
# 60 for demo purposes so you can actually see it update; in production
# this would run once a day, not every minute.
WELLNESS_CHECK_INTERVAL_SECONDS = 60

app = Flask(__name__)
backend = CloudBackend(caregiver_phone="+15551234567", robot_name="Raksha AI Robot")
manager = None  # set in main(), a DecisionManager instance
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


# ---- NEW: Memory Engine endpoints ----

@app.route("/memory", methods=["GET"])
def get_memory():
    """Everything the Memory & Companion dashboard card needs."""
    if manager is None:
        return jsonify({"error": "System not started yet"}), 503
    return jsonify({
        "family_members": manager.memory.get_family_members(),
        "medications": manager.memory.get_medications(),
        "important_dates": manager.memory.get_important_dates(),
        "preferences": manager.memory.get_all_preferences(),
        "context_summary": manager.memory.get_context_summary(),
    })


# ---- NEW: Wellness Engine endpoint ----

@app.route("/wellness", methods=["GET"])
def get_wellness():
    """Everything the Wellness & Analytics dashboard screen needs."""
    if manager is None:
        return jsonify({"error": "System not started yet"}), 503
    score = manager.wellness.get_wellness_score()
    return jsonify({
        "wellness_score": score,               # None until enough history exists
        "today_active_seconds": manager.wellness._today_active_seconds,
        "anomaly_flagged": manager.last_wellness_flag,
    })


# ---- NEW: Routine Engine endpoint ----

@app.route("/routine", methods=["GET"])
def get_routine():
    """Wake/sleep time proxy, interaction count, and medication adherence."""
    if manager is None:
        return jsonify({"error": "System not started yet"}), 503
    routine = manager.wellness.get_routine_summary()
    med_names = [m["name"] for m in manager.memory.get_medications()]
    adherence = manager.wellness.get_medication_adherence_today(med_names)
    routine["medication_adherence_pct"] = adherence
    routine["scheduled_medications"] = med_names
    return jsonify(routine)


@app.route("/medication/taken", methods=["POST"])
def mark_medication_taken():
    """
    Lets the caregiver dashboard mark a dose as taken.
    Expects JSON body: {"medication_name": "Metformin"}
    """
    if manager is None:
        return jsonify({"error": "System not started yet"}), 503
    body = request.get_json(force=True, silent=True) or {}
    name = body.get("medication_name")
    if not name:
        return jsonify({"error": "Expected {'medication_name': <string>}"}), 400
    manager.wellness.record_medication_taken(name)
    return jsonify({"success": True, "medication_name": name})


# ---- NEW: Accessibility Profile endpoints (GET current, POST to update) ----

@app.route("/accessibility", methods=["GET"])
def get_accessibility():
    """Everything the Accessibility Profile dashboard screen needs."""
    if manager is None:
        return jsonify({"error": "System not started yet"}), 503
    profile = manager.accessibility_profile
    return jsonify({
        "hearing_impaired": profile.get_need("hearing_impaired"),
        "vision_impaired": profile.get_need("vision_impaired"),
        "dyslexia": profile.get_need("dyslexia"),
        "mobility_challenge": profile.get_need("mobility_challenge"),
        "adapted_settings": manager.get_accessibility_settings(),
    })


@app.route("/accessibility", methods=["POST"])
def set_accessibility():
    """
    Lets the caregiver dashboard toggle a need on/off.
    Expects JSON body: {"need": "hearing_impaired", "enabled": true}
    """
    if manager is None:
        return jsonify({"error": "System not started yet"}), 503
    body = request.get_json(force=True, silent=True) or {}
    need = body.get("need")
    enabled = body.get("enabled")
    valid_needs = {"hearing_impaired", "vision_impaired", "dyslexia", "mobility_challenge"}
    if need not in valid_needs or not isinstance(enabled, bool):
        return jsonify({"error": "Expected {'need': <one of %s>, 'enabled': true|false}" % valid_needs}), 400
    manager.accessibility_profile.set_need(need, enabled)
    return jsonify({"success": True, "need": need, "enabled": enabled})


def run_dashboard_server():
    app.run(host="0.0.0.0", port=DASHBOARD_PORT, debug=False, use_reloader=False)


def main():
    global latest_status, manager

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

    manager = DecisionManager(
        on_state_change=on_state_change,
        on_verification_prompt=hw.speak,
    )

    server_thread = threading.Thread(target=run_dashboard_server, daemon=True)
    server_thread.start()

    print(f"\nDashboard should point to: http://localhost:{DASHBOARD_PORT}/digital_twin")
    print("New endpoints available: /memory  /wellness  /accessibility")
    print("Open Module_5/dashboard.html in your browser now.\n")
    print("Starting camera loop... (Ctrl+C to stop)\n")

    last_state = None
    last_accessibility_mode = None
    frame_count = 0
    cached_hazard_in_path = False
    cached_hazard_type = None
    fps_counter = 0
    fps_timer_start = time.time()
    last_wellness_check = time.time()

    try:
        while True:
            loop_start = time.time()
            frame = cam.get_frame()
            frame_count += 1

            fall_suspected = pose_detector.process(frame)
            gesture = hand_detector.process(frame)
            pain_index = face_detector.process(frame)

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

            # DecisionManager routes through Safety Engine internally AND
            # feeds the Wellness Engine's movement tracker.
            manager.process_telemetry(output)
            current_state = manager.safety.current_state
            current_accessibility_mode = manager.safety.accessibility_mode

            # NEW: Routine Engine -- count a real interaction whenever a
            # gesture is detected, or a hazard/pain reading suggests a
            # person is actually present and active (not just an empty room).
            if output.get("detected_gesture") or output.get("pain_index", 0) > 0:
                manager.wellness.record_interaction(output.get("timestamp"))

            backend.log_telemetry(output, robot_state=current_state)
            backend.sync_digital_twin(
                output, robot_state=current_state,
                accessibility_mode=current_accessibility_mode
            )

            if (current_state != last_state or
                    current_accessibility_mode != last_accessibility_mode):
                hw.enforce_hardware_profile(
                    current_state,
                    accessibility_mode=current_accessibility_mode,
                    raw_left_pwm=DEMO_LEFT_PWM,
                    raw_right_pwm=DEMO_RIGHT_PWM,
                )
                last_state = current_state
                last_accessibility_mode = current_accessibility_mode

            # Periodic Wellness Engine check (demo interval; see constant above)
            if time.time() - last_wellness_check >= WELLNESS_CHECK_INTERVAL_SECONDS:
                is_anomaly, today, baseline = manager.check_wellness()
                print(f"[Wellness] today={today}s baseline={baseline} anomaly={is_anomaly}")
                last_wellness_check = time.time()

            elapsed = time.time() - loop_start
            sleep_time = FRAME_INTERVAL - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

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
