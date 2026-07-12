"""
mode_manager.py
Module 2: The Decision & Orchestration Layer (Mode Manager)

Reads live telemetry from Module 1 and decides which state the robot
should be in: CONVERSATION, ACCESSIBILITY (Vision or Hearing sub-mode),
or SAFETY_ALERT.

IMPORTANT — adapted to match Module 1's REAL JSON output:
  {"timestamp": ..., "fall_suspected": bool, "detected_gesture": str/null,
   "pain_index": 0-10, "hazard_in_path": bool, "hazard_type": str/null}

Real trigger mapping used here, matching the original project architecture
(Pi Camera pipelines -> Accessibility sub-modes):
  - SAFETY_ALERT               -> fall_suspected (after Double-Verification),
                                  OR pain_index staying high for several seconds
  - ACCESSIBILITY (Vision)     -> hazard_in_path is True (YOLO object detection
                                  helping someone who can't see well navigate
                                  around an obstacle)
  - ACCESSIBILITY (Hearing)    -> detected_gesture == "Wave" (MediaPipe Hands
                                  sign/gesture use, helping someone who can't
                                  hear communicate visually instead)
  - CONVERSATION               -> default / normal state
"""

import time


class RobotState:
    CONVERSATION = "CONVERSATION"
    ACCESSIBILITY = "ACCESSIBILITY"
    SAFETY_ALERT = "SAFETY_ALERT"


class AccessibilityMode:
    VISION = "VISION_IMPAIRED"
    HEARING = "HEARING_IMPAIRED"
    NONE = None


VERIFY_WINDOW_SECONDS = 5.0   # how long to wait for a "Thumbs_Up" before escalating
HIGH_PAIN_THRESHOLD = 6       # pain_index at/above this counts as "high"
HIGH_PAIN_SUSTAIN_SECONDS = 3.0  # how long high pain must persist to escalate


class ModeManager:
    def __init__(self, on_state_change=None, on_verification_prompt=None):
        """
        on_state_change: optional callback(old_state, new_state, data) called
        whenever the state actually changes -- this is where Module 3
        (hardware bridge) would hook in later.

        on_verification_prompt: optional callback(message) called when the
        double-verification loop needs to ask the person something out loud
        (e.g. "Are you okay?") -- Module 3 can use this to actually speak it.
        """
        self.current_state = RobotState.CONVERSATION
        self.accessibility_mode = AccessibilityMode.NONE
        self.on_state_change = on_state_change
        self.on_verification_prompt = on_verification_prompt

        # Double-verification loop bookkeeping
        self.double_verify_active = False
        self.verification_start_time = 0

        # High-pain sustain tracking
        self._pain_high_since = None

    def process_telemetry(self, data: dict):
        """
        data: the parsed JSON dict from Module 1 (already a dict, not a string).
        """
        fall_suspected = data.get("fall_suspected", False)
        detected_gesture = data.get("detected_gesture")
        pain_index = data.get("pain_index", 0)
        hazard_in_path = data.get("hazard_in_path", False)
        hazard_type = data.get("hazard_type")

        # ---- 1. Double-Verification Safety Loop ----
        if fall_suspected and not self.double_verify_active:
            print("[Decision Engine] Sudden movement flagged. "
                  "Locking motors, asking: 'Are you okay?'")
            self.double_verify_active = True
            self.verification_start_time = time.time()
            if self.on_verification_prompt:
                self.on_verification_prompt("I noticed a sharp movement. Are you doing alright?")
            return

        if self.double_verify_active:
            if detected_gesture == "Thumbs_Up":
                print("[Decision Engine] Thumbs-up received. False alarm cleared. "
                      "Resuming normal operation.")
                self.double_verify_active = False
                if self.on_verification_prompt:
                    self.on_verification_prompt("Glad to hear you're okay!")
                return

            elapsed = time.time() - self.verification_start_time
            if elapsed > VERIFY_WINDOW_SECONDS:
                print("[Decision Engine] No confirmation received in time. Escalating.")
                self.double_verify_active = False
                self._set_state(RobotState.SAFETY_ALERT, data)
                self._trigger_emergency_pipeline("no_response_after_fall")
                return

            # Still waiting -- don't fall through to normal state logic yet
            return

        # ---- 2. Sustained high pain_index (independent of falls) ----
        if pain_index >= HIGH_PAIN_THRESHOLD:
            if self._pain_high_since is None:
                self._pain_high_since = time.time()
            elif (time.time() - self._pain_high_since >= HIGH_PAIN_SUSTAIN_SECONDS
                    and self.current_state != RobotState.SAFETY_ALERT):
                self._set_state(RobotState.SAFETY_ALERT, data)
                self._trigger_emergency_pipeline("sustained_high_pain_index")
                return
        else:
            self._pain_high_since = None

        # ---- 3. Standard state orchestration ----
        if self.current_state == RobotState.SAFETY_ALERT:
            # Stay in Safety Alert until something external clears it
            # (in the full system, Module 3/caregiver ack would reset this)
            return

        if hazard_in_path:
            self._set_accessibility(AccessibilityMode.VISION, data, hazard_type)
        elif detected_gesture == "Wave":
            self._set_accessibility(AccessibilityMode.HEARING, data, None)
        else:
            self.accessibility_mode = AccessibilityMode.NONE
            self._set_state(RobotState.CONVERSATION, data)

    def _set_accessibility(self, sub_mode, data, hazard_type):
        mode_changed = sub_mode != self.accessibility_mode
        self.accessibility_mode = sub_mode
        self._set_state(RobotState.ACCESSIBILITY, data)
        if mode_changed:
            if sub_mode == AccessibilityMode.VISION:
                print(f"[Decision Engine] Vision-Impaired Mode active "
                      f"(obstacle detected: {hazard_type}). Switching to slow, "
                      f"careful navigation with audio guidance.")
            elif sub_mode == AccessibilityMode.HEARING:
                print("[Decision Engine] Hearing-Impaired Mode active "
                      "(sign/gesture detected). Switching to large text/visual "
                      "display instead of voice.")

    def _set_state(self, new_state, data):
        if new_state != self.current_state:
            old_state = self.current_state
            print(f"[Decision Engine] State change: {old_state} -> {new_state}")
            self.current_state = new_state
            if self.on_state_change:
                self.on_state_change(old_state, new_state, data)

    def _trigger_emergency_pipeline(self, reason):
        print(f"[CRITICAL] Escalating to SAFETY_ALERT (reason: {reason}). "
              f"Would notify Module 3 (hardware freeze) and Module 4 (cloud SOS) here.")

    def reset_safety_alert(self):
        """Call this once a caregiver/teammate module acknowledges the emergency."""
        print("[Decision Engine] Safety alert manually cleared. Resuming normal operation.")
        self.current_state = RobotState.CONVERSATION
        self.accessibility_mode = AccessibilityMode.NONE