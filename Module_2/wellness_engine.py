"""
wellness_engine.py
Module 2, Engine 4: Routine Learning & Wellness Engine

Learns a simple daily activity baseline over time and flags when
today's activity is significantly below normal -- an early, gentle
signal of possible mobility decline, without needing a fall to
actually happen.

DELIBERATELY LIGHTWEIGHT: real routine-learning could use proper time
series ML. On a Raspberry Pi 5, with no labeled training data
available, a rolling average + standard deviation comparison is a
practical, honest MVP -- fast, explainable, and good enough to catch
genuinely large deviations, per the brief's request for "lightweight
ML and analytics suitable for Raspberry Pi 5."

Activity is measured here as "seconds of detected movement per day"
(derived from Module 1's pose data over time), as a simple proxy for
the "meters walked" example in the brief -- we don't have distance
measurement without additional sensors (e.g. wheel encoders or a
pedometer), so movement-time is the practical stand-in.

EXPANDED (Routine Engine additions):
- Wake/sleep time: derived from the first and last recorded
  interaction of the day, not a separate sensor -- an honest proxy,
  not true sleep-tracking.
- Interaction frequency: a simple per-day counter of telemetry
  readings that represent a real interaction (a gesture, or any
  frame where a person was detected).
- Medication adherence: a real log the caregiver dashboard can write
  to when a dose is marked taken, compared against how many doses
  were scheduled for the day (from Memory Engine's medication list).
"""

import sqlite3
import os
import time
import statistics

DB_PATH = os.path.join(os.path.dirname(__file__), "wellness.db")

BASELINE_MIN_DAYS = 5          # need at least this many days before flagging anomalies
ANOMALY_THRESHOLD_STDDEVS = 1.5  # how far below baseline counts as concerning


class WellnessEngine:
    def __init__(self):
        self._init_db()
        self._today_active_seconds = 0
        self._last_update_time = time.time()

        # --- Routine Engine additions ---
        self._today_date = time.strftime("%Y-%m-%d")
        self._today_first_interaction = None   # epoch seconds, proxy for "wake time"
        self._today_last_interaction = None    # epoch seconds, proxy for "sleep time"
        self._today_interaction_count = 0

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_activity (
                date TEXT PRIMARY KEY,
                active_seconds INTEGER
            )
        """)
        # --- Routine Engine additions ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_routine (
                date TEXT PRIMARY KEY,
                first_interaction INTEGER,
                last_interaction INTEGER,
                interaction_count INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medication_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                medication_name TEXT,
                taken_at INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def record_movement_tick(self, is_moving, tick_seconds=1.0):
        """
        Call this periodically (e.g. once per second) with whether the
        person is currently moving (from Module 1's pose data).
        Accumulates today's total active time.
        """
        self._roll_day_if_needed()
        if is_moving:
            self._today_active_seconds += tick_seconds

    def record_interaction(self, timestamp=None):
        """
        NEW: call this whenever a real interaction happens -- e.g. a
        gesture was detected, or simply that a person was in frame.
        Tracks the first and last interaction of the day (a proxy for
        wake/sleep time) and a running interaction count.
        """
        self._roll_day_if_needed()
        ts = timestamp or time.time()
        if self._today_first_interaction is None:
            self._today_first_interaction = ts
        self._today_last_interaction = ts
        self._today_interaction_count += 1

    def _roll_day_if_needed(self):
        """If the date has changed since we started, save yesterday's
        routine data and reset today's counters."""
        current_date = time.strftime("%Y-%m-%d")
        if current_date != self._today_date:
            self._save_routine_row(self._today_date)
            self._today_date = current_date
            self._today_first_interaction = None
            self._today_last_interaction = None
            self._today_interaction_count = 0

    def _save_routine_row(self, date_str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO daily_routine (date, first_interaction, last_interaction, interaction_count) VALUES (?, ?, ?, ?)",
            (date_str, self._today_first_interaction, self._today_last_interaction, self._today_interaction_count)
        )
        conn.commit()
        conn.close()

    def record_medication_taken(self, medication_name):
        """
        NEW: call this when a caregiver/user marks a dose as taken
        (e.g. a dashboard button). Logs a real, timestamped row.
        """
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO medication_log (date, medication_name, taken_at) VALUES (?, ?, ?)",
            (time.strftime("%Y-%m-%d"), medication_name, int(time.time()))
        )
        conn.commit()
        conn.close()

    def get_medication_adherence_today(self, scheduled_medication_names):
        """
        NEW: compares today's logged doses against the list of
        medications known to Memory Engine. Returns a 0-100 percentage,
        or None if there are no scheduled medications to compare against.
        scheduled_medication_names: list of medication name strings
        (pass in from MemoryEngine.get_medications()).
        """
        if not scheduled_medication_names:
            return None

        today_str = time.strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT DISTINCT medication_name FROM medication_log WHERE date = ?",
            (today_str,)
        ).fetchall()
        conn.close()

        taken_names = {r[0] for r in rows}
        scheduled_set = set(scheduled_medication_names)
        taken_count = len(taken_names & scheduled_set)

        return round((taken_count / len(scheduled_set)) * 100)

    def get_routine_summary(self):
        """
        NEW: returns today's wake/sleep-time proxy and interaction
        count, plus a 7-day average wake/sleep time if enough history
        exists.
        """
        def fmt(ts):
            return time.strftime("%I:%M %p", time.localtime(ts)) if ts else None

        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT first_interaction, last_interaction FROM daily_routine "
            "WHERE date != ? ORDER BY date DESC LIMIT 7",
            (self._today_date,)
        ).fetchall()
        conn.close()

        avg_wake = None
        avg_sleep = None
        valid_wakes = [r[0] for r in rows if r[0]]
        valid_sleeps = [r[1] for r in rows if r[1]]
        if valid_wakes:
            # Average time-of-day, not full timestamp -- convert to seconds-since-midnight first
            wake_seconds = [ts % 86400 for ts in valid_wakes]
            avg_wake_seconds = statistics.mean(wake_seconds)
            avg_wake = time.strftime("%I:%M %p", time.gmtime(avg_wake_seconds))
        if valid_sleeps:
            sleep_seconds = [ts % 86400 for ts in valid_sleeps]
            avg_sleep_seconds = statistics.mean(sleep_seconds)
            avg_sleep = time.strftime("%I:%M %p", time.gmtime(avg_sleep_seconds))

        return {
            "today_wake_time": fmt(self._today_first_interaction),
            "today_sleep_time": fmt(self._today_last_interaction),
            "today_interaction_count": self._today_interaction_count,
            "avg_wake_time_7day": avg_wake,
            "avg_sleep_time_7day": avg_sleep,
        }

    def save_today_and_check_anomaly(self):
        """
        Call this once at the end of a day (or periodically during
        testing) to persist today's total and check for anomalies
        against the learned baseline.
        Returns: (is_anomaly: bool, today_seconds, baseline_seconds or None)
        """
        today_str = time.strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO daily_activity (date, active_seconds) VALUES (?, ?)",
            (today_str, int(self._today_active_seconds))
        )
        conn.commit()

        rows = conn.execute(
            "SELECT active_seconds FROM daily_activity WHERE date != ? ORDER BY date DESC LIMIT 14",
            (today_str,)
        ).fetchall()
        conn.close()

        history = [r[0] for r in rows]

        if len(history) < BASELINE_MIN_DAYS:
            return False, self._today_active_seconds, None  # not enough history yet

        baseline_mean = statistics.mean(history)
        baseline_stddev = statistics.stdev(history) if len(history) > 1 else 0

        threshold = baseline_mean - (ANOMALY_THRESHOLD_STDDEVS * baseline_stddev)
        is_anomaly = self._today_active_seconds < threshold and self._today_active_seconds < baseline_mean * 0.5

        return is_anomaly, self._today_active_seconds, baseline_mean

    def get_wellness_score(self):
        """
        A simple 0-100 score: 100 = activity matches or exceeds
        baseline, lower = more below baseline. Rough, explainable,
        not a clinical measure.
        """
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT active_seconds FROM daily_activity ORDER BY date DESC LIMIT 14"
        ).fetchall()
        conn.close()
        history = [r[0] for r in rows]

        if len(history) < BASELINE_MIN_DAYS:
            return None  # not enough data to score yet

        baseline_mean = statistics.mean(history)
        if baseline_mean == 0:
            return None

        ratio = self._today_active_seconds / baseline_mean
        score = min(100, max(0, round(ratio * 100)))
        return score

    def reset_today(self):
        """Call at the start of a new day (or between test runs)."""
        self._today_active_seconds = 0
