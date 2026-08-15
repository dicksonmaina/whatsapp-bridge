#!/usr/bin/env python3
"""
barcode_qr_tool.py - Local, free QR code + barcode reading.
Uses OpenCV (QR, built in) with an optional pyzbar fallback for
1D barcodes (UPC/EAN/Code128 etc). No API, no billing.

Optional for 1D barcodes:
    sudo apt install libzbar0
    pip install pyzbar --break-system-packages
"""

import os
import cv2

try:
    from pyzbar.pyzbar import decode as zbar_decode
    HAS_ZBAR = True
except ImportError:
    HAS_ZBAR = False


def scan_codes(path: str) -> dict:
    """
    Detect and decode QR codes and (if pyzbar installed) barcodes
    in an image. Returns a plain dict.
    """
    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    img = cv2.imread(path)
    if img is None:
        return {"error": "could not read image (unsupported format?)"}

    results = []

    # QR codes via OpenCV (no extra deps)
    detector = cv2.QRCodeDetector()
    retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
    if retval:
        for info, pts in zip(decoded_info, points):
            if info:
                results.append({
                    "type": "QRCODE",
                    "data": info,
                    "box": pts.tolist() if pts is not None else None,
                })

    # 1D barcodes + extra QR coverage via pyzbar, if available
    if HAS_ZBAR:
        for obj in zbar_decode(img):
            results.append({
                "type": obj.type,
                "data": obj.data.decode("utf-8", errors="replace"),
                "box": [[p.x, p.y] for p in obj.polygon],
            })

    return {
        "file": os.path.basename(path),
        "codes_found": len(results),
        "codes": results,
        "barcode_support": HAS_ZBAR,
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "scan_codes",
            "description": (
                "Detect and decode QR codes (and barcodes, if pyzbar is "
                "installed) in a local image. Free, local, no API calls."
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
        print("Usage: python3 barcode_qr_tool.py <image_path>")
        sys.exit(1)
    print(json.dumps(scan_codes(sys.argv[1]), indent=2))
