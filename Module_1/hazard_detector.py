"""
hazard_detector.py
Pipeline D: Hazard Parsing via YOLOv8-nano.

Logic:
- Run a lightweight pre-trained YOLOv8 object detection loop.
- Filter detections to specific hazard classes (see HAZARD_CLASSES).
- If a hazard is detected in the lower half of the frame (i.e. on the
  floor, in the walking path), flag hazard_detected = True and report
  its type.

NOTE: YOLOv8's default COCO weights only include "backpack" and
"handbag" as trained classes -- "wire" and "shoes" are NOT standard
COCO classes. To detect those two reliably you'll eventually want a
custom-trained/fine-tuned model. For now this script:
  1. Filters for backpack/handbag out of the box.
  2. Leaves "wire" and "shoes" in the filter list so the code is ready
     to go the moment you drop in a custom-trained model into
     models/ that does recognize them.
"""

from ultralytics import YOLO

HAZARD_CLASSES = {"backpack", "handbag", "wire", "shoes"}
CONFIDENCE_THRESHOLD = 0.4


class HazardDetector:
    def __init__(self, model_path="yolov8n.pt"):
        # First run will auto-download yolov8n.pt (~6MB) if not present locally.
        self.model = YOLO(model_path)
        self.class_names = self.model.names  # id -> name mapping

    def process(self, frame_rgb):
        """
        frame_rgb: numpy array (H, W, 3) in RGB.
        Returns: (hazard_detected: bool, hazard_type: str or None)
        """
        h, w, _ = frame_rgb.shape
        results = self.model(frame_rgb, verbose=False)[0]

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = self.class_names.get(cls_id, "")

            if name not in HAZARD_CLASSES or conf < CONFIDENCE_THRESHOLD:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            box_center_y = (y1 + y2) / 2

            # "Lower half of the camera coordinate grid" = floor/path area
            if box_center_y > (h / 2):
                return True, name

        return False, None

    def close(self):
        pass  # ultralytics YOLO doesn't need explicit cleanup


if __name__ == "__main__":
    import cv2
    from camera import RakshaCamera  # auto-detects Pi camera vs. laptop webcam

    cam = RakshaCamera().start()
    detector = HazardDetector()
    print("Hazard detector running. Press 'q' to quit.")

    try:
        while True:
            frame = cam.get_frame()
            hazard, htype = detector.process(frame)

            label = f"HAZARD: {htype}" if hazard else "Clear"
            color = (0, 0, 255) if hazard else (0, 255, 0)
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.imshow("Hazard Detector Test", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()
        cam.stop()
