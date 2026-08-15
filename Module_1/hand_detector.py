"""
hand_detector.py
Pipeline B: Accessibility Input via MediaPipe Hands.

Detects three gestures:
- "Thumbs_Up"   -> thumb up, other 4 fingers curled closed
- "Thumbs_Down" -> thumb down, other 4 fingers curled closed
- "Wave"        -> open palm (all 5 fingers extended) moving side-to-side
                   (used for a "Hi" / "Bye" style wave)
Returns None if no recognized gesture is showing.
"""

from collections import deque
import math
import mediapipe as mp

mp_hands = mp.solutions.hands

# Landmark indices
THUMB_TIP, THUMB_IP, THUMB_MCP = 4, 2, 1
WRIST = 0

# (tip, pip, mcp) for the other four fingers -- mcp is the base knuckle
FINGER_LANDMARKS = [
    (8, 6, 5),     # Index
    (12, 10, 9),   # Middle
    (16, 14, 13),  # Ring
    (20, 18, 17),  # Pinky
]

EXTENDED_RATIO = 1.3   # tip must be this many times farther from wrist than mcp to count as "extended"
CURLED_RATIO = 1.1     # tip must be closer to wrist than this multiple of mcp distance to count as "curled"

WAVE_HISTORY_LEN = 5         # how many frames of wrist x-position to remember (lower = faster to trigger)
WAVE_MIN_RANGE = 0.035       # total left-right movement range needed (normalized 0-1 scale)
WAVE_MIN_DIRECTION_CHANGES = 1   # at least one left-right-left (or right-left-right) swing
WAVE_DEADZONE = 0.006        # ignore movement smaller than this as noise


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


class HandDetector:
    def __init__(self):
        self.hands = mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._wrist_x_history = deque(maxlen=WAVE_HISTORY_LEN)
        self._last_finger_states = []

    def process(self, frame_rgb):
        """
        frame_rgb: numpy array (H, W, 3) in RGB.
        Returns: "Thumbs_Up", "Thumbs_Down", "Wave", or None
        """
        results = self.hands.process(frame_rgb)
        if not results.multi_hand_landmarks:
            self._wrist_x_history.clear()
            return None

        lm = results.multi_hand_landmarks[0].landmark
        wrist = lm[WRIST]

        # Distance-based finger state -- robust to hand rotation/tilt
        finger_states = []
        for tip_i, pip_i, mcp_i in FINGER_LANDMARKS:
            tip_dist = _dist(lm[tip_i], wrist)
            mcp_dist = _dist(lm[mcp_i], wrist)
            if mcp_dist == 0:
                finger_states.append("unknown")
                continue
            ratio = tip_dist / mcp_dist
            if ratio > EXTENDED_RATIO:
                finger_states.append("extended")
            elif ratio < CURLED_RATIO:
                finger_states.append("curled")
            else:
                finger_states.append("unknown")

        fingers_curled = all(s == "curled" for s in finger_states)
        fingers_extended = all(s == "extended" for s in finger_states)
        self._last_finger_states = finger_states  # for debugging

        # Thumb direction relative to its own base (rotation-tolerant enough for up/down)
        thumb_dist = _dist(lm[THUMB_TIP], wrist)
        thumb_base_dist = _dist(lm[THUMB_MCP], wrist)
        thumb_extended = thumb_dist > thumb_base_dist * EXTENDED_RATIO
        thumb_up = thumb_extended and lm[THUMB_TIP].y < lm[THUMB_IP].y
        thumb_down = thumb_extended and lm[THUMB_TIP].y > lm[THUMB_IP].y

        if thumb_up and fingers_curled:
            self._wrist_x_history.clear()
            return "Thumbs_Up"

        if thumb_down and fingers_curled:
            self._wrist_x_history.clear()
            return "Thumbs_Down"

        # Open palm: check for a side-to-side waving motion over recent frames
        if fingers_extended:
            self._wrist_x_history.append(wrist.x)
            if self._is_waving():
                return "Wave"
            return None

        self._wrist_x_history.clear()
        return None

    def _is_waving(self):
        """
        Looks for a real side-to-side wave: the wrist must cover a decent
        total left-right RANGE, and change direction at least once.
        Using total range (not just per-frame deltas) makes this robust
        to different waving speeds.
        """
        if len(self._wrist_x_history) < self._wrist_x_history.maxlen:
            return False

        xs = list(self._wrist_x_history)
        total_range = max(xs) - min(xs)
        if total_range < WAVE_MIN_RANGE:
            return False

        # Count direction changes, ignoring tiny noise movements
        direction_changes = 0
        last_direction = None
        for i in range(1, len(xs)):
            delta = xs[i] - xs[i - 1]
            if abs(delta) < WAVE_DEADZONE:
                continue
            direction = "right" if delta > 0 else "left"
            if last_direction and direction != last_direction:
                direction_changes += 1
            last_direction = direction

        return direction_changes >= WAVE_MIN_DIRECTION_CHANGES

    def close(self):
        self.hands.close()


if __name__ == "__main__":
    import cv2
    from camera import RakshaCamera  # auto-detects Pi camera vs. laptop webcam

    cam = RakshaCamera().start()
    detector = HandDetector()
    print("Hand detector running. Press 'q' to quit.")

    try:
        while True:
            frame = cam.get_frame()
            gesture = detector.process(frame)

            label = gesture if gesture else "No gesture"
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

            # Debug info: show finger states and wave progress on screen
            debug_y = 80
            cv2.putText(frame, f"History len: {len(detector._wrist_x_history)}/{WAVE_HISTORY_LEN}",
                        (20, debug_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            cv2.putText(frame, f"Fingers: {detector._last_finger_states}",
                        (20, debug_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            history_str = ", ".join(f"{x:.3f}" for x in detector._wrist_x_history)
            cv2.putText(frame, f"Wrist X: {history_str}",
                        (20, debug_y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            if len(detector._wrist_x_history) > 0:
                xs = list(detector._wrist_x_history)
                current_range = max(xs) - min(xs)
                cv2.putText(frame, f"Range: {current_range:.3f} (need {WAVE_MIN_RANGE})",
                            (20, debug_y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

            cv2.imshow("Hand Detector Test", frame)

            if gesture:
                print(f"\n>>> GESTURE DETECTED: {gesture} <<<\n")

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()
        cam.stop()
        detector.close()