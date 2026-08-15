#!/usr/bin/env python3
"""
image_convert_tool.py - Local, free image resize/format conversion.
Pure Pillow. No API, no billing.
"""

import os
from PIL import Image


def convert_image(path: str, out_path: str = None, format: str = None,
                   max_width: int = None, max_height: int = None,
                   quality: int = 90) -> dict:
    """
    Resize and/or convert an image format. Keeps aspect ratio if only
    one of max_width/max_height is given.
    """
    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    img = Image.open(path)
    orig_size = img.size

    if max_width or max_height:
        w, h = img.size
        if max_width and not max_height:
            max_height = int(h * (max_width / w))
        elif max_height and not max_width:
            max_width = int(w * (max_height / h))
        img.thumbnail((max_width, max_height))

    if not out_path:
        base, ext = os.path.splitext(path)
        new_ext = f".{format.lower()}" if format else ext
        out_path = f"{base}_converted{new_ext}"

    save_kwargs = {}
    fmt = (format or img.format or "PNG").upper()
    if fmt in ("JPEG", "JPG"):
        fmt = "JPEG"
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        save_kwargs["quality"] = quality

    img.save(out_path, format=fmt, **save_kwargs)

    return {
        "output": out_path,
        "original_size": list(orig_size),
        "new_size": list(img.size),
        "format": fmt,
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "convert_image",
            "description": (
                "Resize and/or convert an image's file format (e.g. PNG->JPEG, "
                "downscale for sending). Free, local, no API calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to source image"},
                    "out_path": {"type": "string", "description": "Optional output path"},
                    "format": {"type": "string", "description": "e.g. 'JPEG', 'PNG', 'WEBP'"},
                    "max_width": {"type": "integer", "description": "Max width in px"},
                    "max_height": {"type": "integer", "description": "Max height in px"},
                },
                "required": ["path"],
            },
        },
    },
]


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python3 image_convert_tool.py <path> [max_width]")
        sys.exit(1)
    mw = int(sys.argv[2]) if len(sys.argv) > 2 else None
    print(json.dumps(convert_image(sys.argv[1], max_width=mw), indent=2))
