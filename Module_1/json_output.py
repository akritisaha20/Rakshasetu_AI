"""
json_output.py
Builds the standardized JSON dictionary that Module 1 outputs to the
other teammates' modules, refreshed at 15 FPS.

Exact schema:
{
  "timestamp": 1720211520,
  "fall_suspected": false,
  "detected_gesture": "Thumbs_Up",
  "pain_index": 2,
  "hazard_in_path": true,
  "hazard_type": "loose_wire"
}
"""

import time
import json


def build_output(fall_suspected, detected_gesture, pain_index,
                  hazard_in_path, hazard_type):
    return {
        "timestamp": int(time.time()),
        "fall_suspected": bool(fall_suspected),
        "detected_gesture": detected_gesture if detected_gesture else None,
        "pain_index": int(pain_index),
        "hazard_in_path": bool(hazard_in_path),
        "hazard_type": hazard_type if hazard_type else None,
    }


def to_json_string(output_dict):
    return json.dumps(output_dict)


if __name__ == "__main__":
    sample = build_output(
        fall_suspected=False,
        detected_gesture="Thumbs_Up",
        pain_index=2,
        hazard_in_path=True,
        hazard_type="wire",
    )
    print(to_json_string(sample))
