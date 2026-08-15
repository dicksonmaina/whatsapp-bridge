#!/usr/bin/env python3
"""
object_detect_tool.py - Local, free object detection via YOLOv8 (nano).
Runs fully offline after the one-time model download. No per-call API,
no billing.

One-time setup:
    pip install ultralytics --break-system-packages
    # first run auto-downloads yolov8n.pt (~6MB) — after that, offline.
"""

import os

try:
    from ultralytics import YOLO
    _model = None
except ImportError:
    YOLO = None
    _model = None


def _get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")  # nano model — fast, small, good enough for most agent use
    return _model


def detect_objects(path: str, confidence: float = 0.4) -> dict:
    """
    Detect objects in an image using YOLOv8n. Returns labels, confidence,
    and bounding boxes.
    """
    if YOLO is None:
        return {"error": "ultralytics not installed. Run: pip install ultralytics --break-system-packages"}

    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    model = _get_model()
    results = model(path, conf=confidence, verbose=False)[0]

    detections = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        label = model.names[cls_id]
        conf = float(box.conf[0])
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
        detections.append({
            "label": label,
            "confidence": round(conf, 3),
            "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        })

    return {
        "file": os.path.basename(path),
        "objects_found": len(detections),
        "objects": detections,
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "detect_objects",
            "description": (
                "Detect and label common objects in a local image (people, "
                "vehicles, animals, everyday items — 80 COCO classes). Free, "
                "local, no API calls after first-time model download."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the image file"},
                    "confidence": {"type": "number", "description": "Min confidence 0-1, default 0.4"},
                },
                "required": ["path"],
            },
        },
    },
]


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python3 object_detect_tool.py <image_path>")
        sys.exit(1)
    print(json.dumps(detect_objects(sys.argv[1]), indent=2))
