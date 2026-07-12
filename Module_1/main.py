"""
main.py
Raksha AI - Module 1
Connects camera + all 4 AI pipelines (pose, hands, face, hazard),
builds a standardized JSON dict at ~15 FPS, and serves it over the
network via a simple HTTP server so teammates' modules can fetch it.

Teammates on the same WiFi network can get the latest reading by
visiting (in a browser, or via code) e.g.:
    http://<this-device's-IP>:5000/status
"""

import time
import json
import threading

from flask import Flask, jsonify

from camera_dev import RakshaCamera
from pose_detector import PoseDetector
from hand_detector import HandDetector
from face_detector import FaceDetector
from hazard_detector import HazardDetector
from json_output import build_output, to_json_string

TARGET_FPS = 15
FRAME_INTERVAL = 1.0 / TARGET_FPS
SERVER_PORT = 5000

app = Flask(__name__)

# Shared state between the detection loop (writer) and the Flask server (reader)
latest_output = {
    "timestamp": int(time.time()),
    "fall_suspected": False,
    "detected_gesture": None,
    "pain_index": 0,
    "hazard_in_path": False,
    "hazard_type": None,
}
output_lock = threading.Lock()


@app.route("/status", methods=["GET"])
def get_status():
    with output_lock:
        return jsonify(latest_output)


def run_server():
    # host="0.0.0.0" makes it reachable from other devices on the same WiFi network,
    # not just this laptop/Pi itself.
    app.run(host="0.0.0.0", port=SERVER_PORT, debug=False, use_reloader=False)


def detection_loop():
    global latest_output

    print("Raksha AI - Module 1 Started")

    cam = RakshaCamera().start()
    pose_detector = PoseDetector()
    hand_detector = HandDetector()
    face_detector = FaceDetector()
    hazard_detector = HazardDetector()

    try:
        while True:
            loop_start = time.time()

            frame = cam.get_frame()

            fall_suspected = pose_detector.process(frame)
            gesture = hand_detector.process(frame)
            pain_index = face_detector.process(frame)
            hazard_in_path, hazard_type = hazard_detector.process(frame)

            output = build_output(
                fall_suspected=fall_suspected,
                detected_gesture=gesture,
                pain_index=pain_index,
                hazard_in_path=hazard_in_path,
                hazard_type=hazard_type,
            )

            with output_lock:
                latest_output = output

            # Still print to terminal too, useful for debugging
            print(to_json_string(output))

            elapsed = time.time() - loop_start
            sleep_time = FRAME_INTERVAL - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nStopping Raksha AI Module 1...")

    finally:
        cam.stop()
        pose_detector.close()
        hand_detector.close()
        face_detector.close()
        hazard_detector.close()


def main():
    # Run the Flask server in a background thread so it doesn't block the camera loop
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"HTTP server running on http://0.0.0.0:{SERVER_PORT}/status")
    print("Teammates on the same WiFi can fetch this from your device's IP address.")

    detection_loop()


if __name__ == "__main__":
    main()
