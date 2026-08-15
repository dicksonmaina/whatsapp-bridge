#!/usr/bin/env python3
"""
image_scan_tool.py - Local, free, no-API image metadata scanner.

Designed to be called as a TOOL by an LLM agent (JARVIS/Hermes) via
function-calling. Pure stdlib + Pillow. No network calls, no billing,
works fully offline.

Import and call directly:
    from image_scan_tool import scan_image, strip_image
    result = scan_image("/path/to/photo.jpg")

Or wire as an LLM tool (OpenAI/Groq-style function schema included below).
"""

import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def _decode_gps(gps_info):
    def to_deg(value):
        d, m, s = value
        return d + (m / 60.0) + (s / 3600.0)

    lat = lon = None
    if 2 in gps_info and 1 in gps_info:
        lat = to_deg(gps_info[2])
        if gps_info[1] == "S":
            lat = -lat
    if 4 in gps_info and 3 in gps_info:
        lon = to_deg(gps_info[4])
        if gps_info[3] == "W":
            lon = -lon
    return lat, lon


def scan_image(path: str) -> dict:
    """
    Scan an image for leaked metadata. Returns a plain dict —
    safe to json.dumps() straight back to an LLM as a tool result.
    """
    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    img = Image.open(path)
    exif_raw = img._getexif() if hasattr(img, "_getexif") else None

    result = {
        "file": os.path.basename(path),
        "format": img.format,
        "size": list(img.size),
        "has_exif": bool(exif_raw),
        "gps": None,
        "device": None,
        "timestamps": {},
        "software": None,
        "field_count": 0,
    }

    if not exif_raw:
        return result

    fields = {}
    gps_info = None
    for tag_id, value in exif_raw.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == "GPSInfo":
            gps_info = {GPSTAGS.get(k, k): v for k, v in value.items()}
            continue
        fields[tag] = value

    if gps_info:
        lat, lon = _decode_gps(gps_info)
        if lat is not None:
            result["gps"] = {
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "maps_url": f"https://maps.google.com/?q={lat:.6f},{lon:.6f}",
            }

    if "Make" in fields or "Model" in fields:
        result["device"] = {
            "make": fields.get("Make"),
            "model": fields.get("Model"),
        }

    for key in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
        if key in fields:
            result["timestamps"][key] = str(fields[key])

    if "Software" in fields:
        result["software"] = str(fields["Software"])

    result["field_count"] = len(fields) + (1 if gps_info else 0)
    return result


def strip_image(path: str, out_path: str = None) -> dict:
    """
    Save a metadata-free copy of the image. Returns dict with output path.
    """
    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    img = Image.open(path)
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))

    if not out_path:
        base, ext = os.path.splitext(path)
        out_path = f"{base}_clean{ext}"

    clean.save(out_path)
    return {"output": out_path, "stripped": True}


# ── LLM tool-calling schema (OpenAI/Groq/Ollama function-call format) ──
# Register these in your agent's tool list so the model can call them
# by name during a conversation (e.g. jarvis_agi.py tool registry).

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "scan_image",
            "description": (
                "Scan a local image file for leaked metadata "
                "(GPS location, device make/model, timestamps, editing "
                "software). Free, local, no API calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the image file",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "strip_image",
            "description": (
                "Create a metadata-free copy of an image, removing GPS, "
                "device, and timestamp data. Free, local, no API calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the image file",
                    },
                    "out_path": {
                        "type": "string",
                        "description": "Optional output path for the clean copy",
                    },
                },
                "required": ["path"],
            },
        },
    },
]


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python3 image_scan_tool.py <image_path>")
        sys.exit(1)
    print(json.dumps(scan_image(sys.argv[1]), indent=2))
