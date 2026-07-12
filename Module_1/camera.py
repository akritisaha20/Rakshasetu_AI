"""
camera.py
Handles the Raspberry Pi Camera Module 3 feed using Picamera2.
Returns raw frames (numpy arrays, RGB) that every AI pipeline
(pose, hands, face, hazard) will consume.
"""

from picamera2 import Picamera2


class RakshaCamera:
    def __init__(self, width=640, height=480):
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


if __name__ == "__main__":
    # Quick standalone test: just show the live feed.
    import cv2

    cam = RakshaCamera().start()
    print("Camera running. Press 'q' to quit.")

    while True:
        frame = cam.get_frame()
        cv2.imshow("Raksha AI - Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
    cam.stop()
