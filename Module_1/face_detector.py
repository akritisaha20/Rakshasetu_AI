"""
face_detector.py
Pipeline C: Distress Tracking via MediaPipe Face Mesh.

Logic:
- Measure mouth openness (13, 14) and eye openness (159, 145),
  normalized against a stable reference distance (between the eyes,
  landmarks 33 and 263) so head distance from camera doesn't skew results.
- Compare against a baseline captured during the first few frames.
- Report a pain_metric 0-10 based on how far current openness deviates
  from that neutral baseline, using an ABSOLUTE difference (not a ratio)
  so tiny natural jitter near a near-zero baseline doesn't cause spikes.
- Smooths over the last few frames to reduce single-frame noise.
"""

import math
from collections import deque
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

# Landmark indices
MOUTH_TOP, MOUTH_BOTTOM = 13, 14
EYE_TOP, EYE_BOTTOM = 159, 145
LEFT_EYE_OUTER, RIGHT_EYE_OUTER = 33, 263  # stable reference for face scale

BASELINE_FRAMES = 30  # ~2 seconds at 15 FPS, used to establish a "neutral" baseline
SMOOTHING_FRAMES = 5  # average over the last N frames to reduce jitter

# How much normalized deviation counts as "maximum" (10/10) distress.
# Tune this up if 10 triggers too easily, down if it never reaches high values.
MAX_EXPECTED_DEVIATION = 0.12


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


class FaceDetector:
    def __init__(self):
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.baseline_mouth_norm = None
        self.baseline_eye_norm = None
        self._mouth_samples = []
        self._eye_samples = []
        self._deviation_history = deque(maxlen=SMOOTHING_FRAMES)

    def process(self, frame_rgb):
        """
        frame_rgb: numpy array (H, W, 3) in RGB.
        Returns: pain_metric int (0-10), or 0 if no face / still calibrating.
        """
        results = self.face_mesh.process(frame_rgb)
        if not results.multi_face_landmarks:
            return 0

        lm = results.multi_face_landmarks[0].landmark

        face_scale = _dist(lm[LEFT_EYE_OUTER], lm[RIGHT_EYE_OUTER])
        if face_scale == 0:
            return 0

        mouth_norm = _dist(lm[MOUTH_TOP], lm[MOUTH_BOTTOM]) / face_scale
        eye_norm = _dist(lm[EYE_TOP], lm[EYE_BOTTOM]) / face_scale

        # Calibration phase: build a baseline of "neutral" face
        if self.baseline_mouth_norm is None:
            self._mouth_samples.append(mouth_norm)
            self._eye_samples.append(eye_norm)
            if len(self._mouth_samples) >= BASELINE_FRAMES:
                self.baseline_mouth_norm = sum(self._mouth_samples) / len(self._mouth_samples)
                self.baseline_eye_norm = sum(self._eye_samples) / len(self._eye_samples)
            return 0

        # Absolute deviation from baseline (not a ratio -- avoids near-zero blowup)
        mouth_deviation = max(0, mouth_norm - self.baseline_mouth_norm)
        eye_deviation = max(0, eye_norm - self.baseline_eye_norm)
        raw_deviation = max(mouth_deviation, eye_deviation)

        # Smooth over the last few frames so single-frame jitter doesn't spike the score
        self._deviation_history.append(raw_deviation)
        smoothed_deviation = sum(self._deviation_history) / len(self._deviation_history)

        pain_metric = int(min(10, max(0, round(
            (smoothed_deviation / MAX_EXPECTED_DEVIATION) * 10
        ))))

        return pain_metric

    def close(self):
        self.face_mesh.close()


if __name__ == "__main__":
    import cv2
    from camera_dev import RakshaCamera  # laptop webcam; swap to `camera` on the Pi

    cam = RakshaCamera().start()
    detector = FaceDetector()
    print("Face detector running (calibrating baseline first). Press 'q' to quit.")

    try:
        while True:
            frame = cam. ()
            pain = detector.process(frame)

            label = f"Pain index: {pain}" if detector.baseline_mouth_norm else "Calibrating..."
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            cv2.imshow("Face Detector Test", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()
        cam.stop()
        detector.close()