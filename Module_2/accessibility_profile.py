"""
accessibility_profile.py
Module 2, Engine 2: Accessibility Adaptation Engine

Stores a user's accessibility needs (a persistent profile, not just
per-frame detection), and translates that profile into concrete
runtime behavior settings the rest of the system can act on.

This works ALONGSIDE Module 1's real-time detection (hazard_in_path ->
Vision-Impaired mode, Wave gesture -> Hearing-Impaired mode) -- that
part already exists in mode_manager.py and is unchanged. This file
adds the missing piece: a standing PROFILE that says "this user has
known hearing loss" so the system can adapt proactively, not just
react to momentary signals.
"""

import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "accessibility_profile.db")


class AccessibilityProfile:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def set_need(self, need_key, enabled):
        """
        need_key: one of "hearing_impaired", "vision_impaired",
        "dyslexia", "mobility_challenge"
        """
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO profile (key, value, updated_at) VALUES (?, ?, ?)",
            (need_key, "true" if enabled else "false", int(time.time()))
        )
        conn.commit()
        conn.close()

    def get_need(self, need_key):
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT value FROM profile WHERE key = ?", (need_key,)).fetchone()
        conn.close()
        return row is not None and row[0] == "true"

    def get_adapted_settings(self):
        """
        Translates the stored profile into concrete runtime settings
        for the rest of the system to use.
        """
        settings = {
            "voice_enabled": True,
            "text_display_mode": "normal",   # normal | large_simple
            "speed_multiplier": 1.0,          # 1.0 = full speed
            "prefer_visual_alerts": False,
        }

        if self.get_need("hearing_impaired"):
            settings["prefer_visual_alerts"] = True
            settings["voice_enabled"] = False

        if self.get_need("vision_impaired"):
            settings["voice_enabled"] = True  # voice becomes essential, not optional

        if self.get_need("dyslexia"):
            settings["text_display_mode"] = "large_simple"

        if self.get_need("mobility_challenge"):
            settings["speed_multiplier"] = 0.5  # extra caution, on top of hazard-based scaling

        return settings
