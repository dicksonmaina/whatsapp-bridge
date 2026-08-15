#!/usr/bin/env python3
"""
face_detect_tool.py - Local, free face detection.
Uses OpenCV's built-in Haar cascades (ships with opencv-python,
no extra download). No API, no billing.

Note: this detects "is there a face and where" — it does NOT identify
who the person is (no facial recognition/matching here).
"""

import os
import cv2


_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
_face_cascade = cv2.CascadeClassifier(_cascade_path)


def detect_faces(path: str, scale_factor: float = 1.1, min_neighbors: int = 5) -> dict:
    """
    Detect faces in an image. Returns bounding boxes, no identity info.
    """
    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    img = cv2.imread(path)
    if img is None:
        return {"error": "could not read image (unsupported format?)"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray, scaleFactor=scale_factor, minNeighbors=min_neighbors, minSize=(30, 30)
    )

    boxes = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in faces]

    return {
        "file": os.path.basename(path),
        "faces_found": len(boxes),
        "faces": boxes,
        "image_size": [img.shape[1], img.shape[0]],
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "detect_faces",
            "description": (
                "Detect faces in a local image and return their bounding "
                "boxes (no identity/recognition, just presence + location). "
                "Free, local, no API calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the image file"}
                },
                "required": ["path"],
            },
        },
    },
]


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python3 face_detect_tool.py <image_path>")
        sys.exit(1)
    print(json.dumps(detect_faces(sys.argv[1]), indent=2))
