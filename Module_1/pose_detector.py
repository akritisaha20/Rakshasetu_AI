"""
pose_detector.py
Pipeline A: Fall Vector Analysis via MediaPipe Pose.

Logic:
- Track shoulders (11, 12) and hips (23, 24) to find the mid-torso
  center point (Xc, Yc).
- Track the change in Yc over time to compute a vertical velocity.
- If velocity crosses a sharp downward threshold AND the person's
  bounding box flips from vertical (width < height) to horizontal
  (width > height), flag fall_suspected = True.
"""

import time
import mediapipe as mp

mp_pose = mp.solutions.pose

# Landmark indices we care about
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24

# Tune these two values on your actual camera/setup
VELOCITY_THRESHOLD = 0.9   # normalized units per second (downward)
MIN_CONFIDENCE = 0.5


class PoseDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(
            model_complexity=0,  # 0=lite (fastest), 1=full, 2=heavy -- use 0 on Raspberry Pi
            min_detection_confidence=MIN_CONFIDENCE,
            min_tracking_confidence=MIN_CONFIDENCE,
        )
        self.prev_yc = None
        self.prev_time = None
        self.prev_orientation_vertical = True

    def process(self, frame_rgb):
        """
        frame_rgb: numpy array (H, W, 3) in RGB.
        Returns: bool fall_suspected
        """
        results = self.pose.process(frame_rgb)
        fall_suspected = False

        if not results.pose_landmarks:
            return fall_suspected

        lm = results.pose_landmarks.landmark

        # Mid-torso center point (normalized 0-1 coordinates)
        xc = (lm[LEFT_SHOULDER].x + lm[RIGHT_SHOULDER].x +
              lm[LEFT_HIP].x + lm[RIGHT_HIP].x) / 4
        yc = (lm[LEFT_SHOULDER].y + lm[RIGHT_SHOULDER].y +
              lm[LEFT_HIP].y + lm[RIGHT_HIP].y) / 4

        # Bounding box from shoulders/hips to determine orientation
        xs = [lm[LEFT_SHOULDER].x, lm[RIGHT_SHOULDER].x, lm[LEFT_HIP].x, lm[RIGHT_HIP].x]
        ys = [lm[LEFT_SHOULDER].y, lm[RIGHT_SHOULDER].y, lm[LEFT_HIP].y, lm[RIGHT_HIP].y]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        is_vertical = width < height

        now = time.time()

        if self.prev_yc is not None and self.prev_time is not None:
            dt = now - self.prev_time
            if dt > 0:
                velocity = (yc - self.prev_yc) / dt  # positive = moving down

                # Fall = fast downward motion + flip from vertical to horizontal posture
                if (velocity > VELOCITY_THRESHOLD and
                        self.prev_orientation_vertical and not is_vertical):
                    fall_suspected = True

        self.prev_yc = yc
        self.prev_time = now
        self.prev_orientation_vertical = is_vertical

        return fall_suspected

    def close(self):
        self.pose.close()


if __name__ == "__main__":
    # Standalone test using the webcam/Pi camera + OpenCV window
    import cv2
    from camera_dev import RakshaCamera  # laptop webcam; swap to `camera` on the Pi

    cam = RakshaCamera().start()
    detector = PoseDetector()
    print("Pose detector running. Press 'q' to quit.")

    try:
        while True:
            frame = cam.get_frame()
            fall = detector.process(frame)

            color = (0, 0, 255) if fall else (0, 255, 0)
            label = "FALL SUSPECTED!" if fall else "OK"
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.imshow("Pose Detector Test", frame)

            if fall:
                print("\n>>> FALL DETECTED! <<<\n")

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()
        cam.stop()
        detector.close()
