"""
camera_dev.py
LAPTOP / WINDOWS development version of the camera module.
Uses your built-in webcam via OpenCV instead of picamera2
(picamera2 only works on the actual Raspberry Pi).

Once you move to the real Raspberry Pi, switch back to camera.py
(the Picamera2 version) -- everything else in the project stays
exactly the same, since both expose get_frame() the same way.
"""

import cv2


class RakshaCamera:
    def __init__(self, width=640, height=480, cam_index=0):
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
    cam = RakshaCamera().start()
    print("Webcam running. Press 'q' to quit.")

    while True:
        frame = cam.get_frame()
        # Convert back to BGR just for correct color display in cv2.imshow
        display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imshow("Raksha AI - Webcam Feed (DEV)", display_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
    cam.stop()
