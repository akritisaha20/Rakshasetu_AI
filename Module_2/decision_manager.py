"""
decision_manager.py
Module 2: Central Decision Manager

The master orchestration layer coordinating all 5 engines:
  1. Safety Engine        (mode_manager.py -- already built, unchanged)
  2. Accessibility Adaptation Engine (accessibility_profile.py)
  3. Memory Engine        (memory_engine.py)
  4. Routine Learning & Wellness Engine (wellness_engine.py)
  5. Companion AI Engine  (companion_engine.py)

PRIORITY HIERARCHY (highest to lowest):
  1. SAFETY       -- a fall or emergency in progress. Nothing else runs.
  2. ACCESSIBILITY -- an active hazard or accessibility need in the moment.
  3. WELLNESS_CONCERN -- a flagged anomaly (e.g. unusually low activity today).
  4. CONVERSATION -- normal companionship, memory, and chat.

This mirrors the Safety Engine's existing states (CONVERSATION,
ACCESSIBILITY, SAFETY_ALERT) and adds WELLNESS_CONCERN as a new,
lower-priority state that surfaces gently rather than interrupting.

STATE TRANSITION RULE: Safety always wins. If the Safety Engine is
mid-verification or already in SAFETY_ALERT, the Decision Manager
short-circuits and ignores requests to the other 4 engines (e.g. a
conversation request gets a polite "please wait" instead of a real
response) -- this is the "prioritize safety over conversation"
requirement from the brief.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from mode_manager import ModeManager, RobotState        # noqa: E402
from accessibility_profile import AccessibilityProfile   # noqa: E402
from memory_engine import MemoryEngine                   # noqa: E402
from wellness_engine import WellnessEngine                # noqa: E402
from companion_engine import CompanionEngine               # noqa: E402


class DecisionPriority:
    SAFETY = "SAFETY"
    ACCESSIBILITY = "ACCESSIBILITY"
    WELLNESS_CONCERN = "WELLNESS_CONCERN"
    CONVERSATION = "CONVERSATION"


class DecisionManager:
    def __init__(self, on_state_change=None, on_verification_prompt=None):
        self.safety = ModeManager(
            on_state_change=on_state_change,
            on_verification_prompt=on_verification_prompt,
        )
        self.accessibility_profile = AccessibilityProfile()
        self.memory = MemoryEngine()
        self.wellness = WellnessEngine()
        self.companion = CompanionEngine(self.memory)

        self.last_wellness_flag = None

    def process_telemetry(self, data: dict):
        """
        Feeds Module 1's telemetry through the Safety Engine (always
        first -- top priority) and returns the current overall
        priority level so the caller (Module 3's hardware bridge, or a
        UI) knows what to do right now.
        """
        self.safety.process_telemetry(data)

        # Feed the Wellness Engine a lightweight movement signal.
        # "Moving" is approximated here as: a fall wasn't just flagged
        # AND the person is in frame (any detection present at all).
        # A real deployment would use a steadier movement signal from
        # Module 1's pose tracking directly.
        is_moving = data.get("fall_suspected") is False
        self.wellness.record_movement_tick(is_moving)

        return self.get_current_priority()

    def get_current_priority(self):
        if self.safety.current_state == RobotState.SAFETY_ALERT or self.safety.double_verify_active:
            return DecisionPriority.SAFETY

        if self.safety.current_state == RobotState.ACCESSIBILITY:
            return DecisionPriority.ACCESSIBILITY

        if self.last_wellness_flag:
            return DecisionPriority.WELLNESS_CONCERN

        return DecisionPriority.CONVERSATION

    def check_wellness(self):
        """
        Call this periodically (e.g. once a day, or on-demand for
        testing) to check for activity anomalies.
        """
        is_anomaly, today, baseline = self.wellness.save_today_and_check_anomaly()
        self.last_wellness_flag = is_anomaly
        return is_anomaly, today, baseline

    def handle_conversation(self, user_text):
        """
        Routes a conversational input through the Companion Engine --
        but ONLY if Safety isn't currently active. This is the concrete
        implementation of "prioritize safety over conversation."
        """
        priority = self.get_current_priority()

        if priority == DecisionPriority.SAFETY:
            return "I need to make sure you're safe first -- one moment."

        return self.companion.generate_response(user_text)

    def get_accessibility_settings(self):
        """Exposes the current adapted behavior settings (speed, voice, text mode)."""
        return self.accessibility_profile.get_adapted_settings()
