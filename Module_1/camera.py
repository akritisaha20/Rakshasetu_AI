"""
camera.py
Unified camera module -- auto-detects real hardware vs. dev laptop, so
you never have to manually swap imports between camera.py/camera_dev.py
again.

- On the real Raspberry Pi (picamera2 installed): uses the Pi Camera
  Module via Picamera2.
- Everywhere else (your Windows laptop, no picamera2): falls back to
  your built-in webcam via OpenCV -- this is exactly what camera_dev.py
  did on its own.

Same graceful-fallback pattern already used in hardware_bridge.py for
pyserial/pyttsx3/winsound/RPi.GPIO/OLED, so this is consistent with
the rest of the project.

Every caller (main.py, pose_detector.py, hand_detector.py,
face_detector.py, hazard_detector.py) should import RakshaCamera from
HERE (`from camera import RakshaCamera`), not from camera_dev directly.
camera_dev.py is kept around standalone in case you ever want to force
webcam mode even on a machine that has picamera2 installed, but nothing
in the pipeline needs to import it directly anymore.
"""

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False


if PICAMERA_AVAILABLE:

    class RakshaCamera:
        """Real Raspberry Pi Camera Module, via Picamera2."""

        def __init__(self, width=640, height=480):
            print("[Camera] picamera2 detected -- using real Raspberry Pi camera.")
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (width, height)}
            )
            self.picam2.configure(config)

        def start(self):
            self.picam2.start()
            return self

        def get_frame(self):
            """Returns a single frame as a numpy array (H, W, 3) in RGB."""
            return self.picam2.capture_array()

        def stop(self):
            self.picam2.stop()

else:

    import cv2

    class RakshaCamera:
        """Dev-laptop fallback: built-in/USB webcam via OpenCV."""

        def __init__(self, width=640, height=480, cam_index=0):
            print("[Camera] picamera2 not available -- falling back to laptop webcam (dev mode).")
            self.cap = cv2.VideoCapture(cam_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        def start(self):
            if not self.cap.isOpened():
                raise RuntimeError("Could not open webcam. Check if another app is using it.")
            return self

        def get_frame(self):
            """Returns a single frame as a numpy array (H, W, 3) in RGB."""
            ret, frame_bgr = self.cap.read()
            if not ret:
                raise RuntimeError("Failed to read frame from webcam.")
            # OpenCV gives BGR by default; MediaPipe/YOLO expect RGB
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            return frame_rgb

        def stop(self):
            self.cap.release()


if __name__ == "__main__":
    # Quick standalone test: just show the live feed, whichever backend got picked.
    import cv2

    cam = RakshaCamera().start()
    print("Camera running. Press 'q' to quit.")

    while True:
        frame = cam.get_frame()
        display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) if not PICAMERA_AVAILABLE else frame
        cv2.imshow("Raksha AI - Camera Feed", display_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
    cam.stop()
