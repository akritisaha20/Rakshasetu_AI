"""
cloud_backend.py
Module 4: The Cloud Backend & Infrastructure

Handles:
- Real local SQLite logging (this part is genuinely functional, no
  account needed -- SQLite is built into Python)
- A simulated "digital twin" sync (writes to a local JSON file standing
  in for Firebase Realtime Database, since no Firebase project is set
  up yet)
- A simulated Dual-Path Alert Gateway (push notification + Twilio call +
  SMS) -- prints clearly labeled messages showing exactly what WOULD be
  sent, ready to swap in real Firebase Admin SDK / Twilio SDK calls
  later once you have accounts set up.
- A Heartbeat/Watchdog check -- flags if telemetry hasn't been received
  recently (simulating "robot went offline" detection).

NOTE: Nothing here requires a Firebase or Twilio account to run and
test. Once you have real accounts, replace the marked SIMULATION
sections with actual `firebase_admin` / `twilio` SDK calls -- the
surrounding logic (when to call them, with what data) stays the same.
"""

import json
import os
import sqlite3
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "raksha_local_logs.db")
DIGITAL_TWIN_PATH = os.path.join(os.path.dirname(__file__), "digital_twin.json")

HEARTBEAT_TIMEOUT_SECONDS = 30  # if no telemetry received in this long, flag OFFLINE


class CloudBackend:
    def __init__(self, caregiver_phone="+1234567890", robot_name="Raksha AI Robot"):
        self.caregiver_phone = caregiver_phone
        self.robot_name = robot_name
        self.last_heartbeat_time = time.time()
        self._init_local_db()

    def _init_local_db(self):
        """Sets up a REAL local SQLite database for telemetry history."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                fall_suspected INTEGER,
                detected_gesture TEXT,
                pain_index INTEGER,
                hazard_in_path INTEGER,
                hazard_type TEXT,
                robot_state TEXT
            )
        """)
        conn.commit()
        conn.close()
        print(f"[Cloud Backend] Local SQLite database ready at: {DB_PATH}")

    def log_telemetry(self, data: dict, robot_state: str):
        """Writes a real row into the local SQLite database."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO telemetry_log
            (timestamp, fall_suspected, detected_gesture, pain_index,
             hazard_in_path, hazard_type, robot_state)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("timestamp", int(time.time())),
            int(data.get("fall_suspected", False)),
            data.get("detected_gesture"),
            data.get("pain_index", 0),
            int(data.get("hazard_in_path", False)),
            data.get("hazard_type"),
            robot_state,
        ))
        conn.commit()
        conn.close()

    def sync_digital_twin(self, data: dict, robot_state: str, accessibility_mode=None):
        """
        SIMULATION: stands in for a real Firebase Realtime Database sync.
        Writes the robot's current status to a local JSON file so you
        can see exactly what a family app would be reading in real time.

        To make this real: replace this with
            firebase_db.reference(f'robots/{robot_id}/telemetry').set(twin)
        """
        twin = {
            "robot_name": self.robot_name,
            "last_updated": int(time.time()),
            "current_mode": robot_state,
            "accessibility_mode": accessibility_mode,
            "emergency_active": robot_state == "SAFETY_ALERT",
            "battery_level": 87,  # placeholder -- would come from real hardware
            "raw_telemetry": data,
        }
        with open(DIGITAL_TWIN_PATH, "w") as f:
            json.dump(twin, f, indent=2)

        self.last_heartbeat_time = time.time()
        return twin

    def check_heartbeat(self):
        """
        Watchdog check: if too long has passed since the last successful
        telemetry sync, the robot is considered OFFLINE.
        Returns True if healthy, False if the connection seems lost.
        """
        elapsed = time.time() - self.last_heartbeat_time
        if elapsed > HEARTBEAT_TIMEOUT_SECONDS:
            print(f"[Cloud Watchdog] ⚠️  No telemetry received in {elapsed:.0f}s. "
                  f"Flagging robot as OFFLINE.")
            return False
        return True

    def dispatch_emergency_alert(self, reason: str):
        """
        SIMULATION: stands in for the real Dual-Path Alert Gateway
        (Firebase Cloud Function + Twilio, per the original blueprint).
        Prints exactly what WOULD be sent through 3 parallel channels.

        To make this real, replace the print statements with:
          - admin.messaging().send(...) for FCM push
          - twilio_client.calls.create(...) for the voice call
          - twilio_client.messages.create(...) for the SMS
        """
        print(f"\n[ALERT GATEWAY] Emergency detected (reason: {reason}). "
              f"Dispatching to {self.caregiver_phone}...")

        print(f"  [Push Notification] 🚨 CRITICAL ALERT: Fall/SOS Detected! "
              f"'{self.robot_name} needs your attention.'")

        print(f"  [Twilio Voice Call SIMULATION] Would call {self.caregiver_phone}: "
              f"\"Alert! {self.robot_name} has detected a possible emergency. "
              f"Please check the app immediately.\"")

        print(f"  [SMS SIMULATION] Would text {self.caregiver_phone}: "
              f"'[Raksha Alert] Emergency detected! Live view: "
              f"https://raksha.app/live?id=robot001'")

        print("[ALERT GATEWAY] All 3 channels dispatched (simulated).\n")

    def get_recent_logs(self, limit=10):
        """Fetches the most recent telemetry entries from the REAL local database."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, fall_suspected, detected_gesture, pain_index,
                   hazard_in_path, hazard_type, robot_state
            FROM telemetry_log
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows
