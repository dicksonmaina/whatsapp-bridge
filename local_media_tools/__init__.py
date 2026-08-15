#!/usr/bin/env python3
"""
local_media_tools.py - Single entry point for all local, free, no-API
media tools. Import this one file into jarvis_agi.py's tool registry.

Covers:
    scan_image        - EXIF metadata leak check
    strip_image        - remove EXIF metadata
    extract_text        - OCR text from images (tesseract)
    convert_image       - resize/format conversion
    scan_codes          - QR + barcode reading
    detect_faces        - face bounding boxes (opencv, no recognition)
    detect_objects      - YOLOv8 object detection      [needs: pip install ultralytics]
    extract_pdf_text    - PDF text extraction           [needs: pip install pypdf]
    transcribe_audio    - Whisper speech-to-text        [needs: pip install openai-whisper]

Each of the above tools also works standalone if you only need one.
"""

from .image_scan_tool import scan_image, strip_image, TOOL_SCHEMAS as _s1
from .image_text_tool import extract_text, TOOL_SCHEMAS as _s2
from .image_convert_tool import convert_image, TOOL_SCHEMAS as _s3
from .barcode_qr_tool import scan_codes, TOOL_SCHEMAS as _s4
from .face_detect_tool import detect_faces, TOOL_SCHEMAS as _s5
from .object_detect_tool import detect_objects, TOOL_SCHEMAS as _s6
from .pdf_text_tool import extract_pdf_text, TOOL_SCHEMAS as _s7
from .speech_to_text_tool import transcribe_audio, TOOL_SCHEMAS as _s8

# Full function-calling schema list — register this with your LLM provider
ALL_TOOL_SCHEMAS = _s1 + _s2 + _s3 + _s4 + _s5 + _s6 + _s7 + _s8

# name -> callable, for dispatch after the model picks a tool
TOOL_DISPATCH = {
    "scan_image": scan_image,
    "strip_image": strip_image,
    "extract_text": extract_text,
    "convert_image": convert_image,
    "scan_codes": scan_codes,
    "detect_faces": detect_faces,
    "detect_objects": detect_objects,
    "extract_pdf_text": extract_pdf_text,
    "transcribe_audio": transcribe_audio,
}


def call_tool(name: str, **kwargs) -> dict:
    """Generic dispatcher: call_tool('extract_text', path='/tmp/x.png')"""
    fn = TOOL_DISPATCH.get(name)
    if not fn:
        return {"error": f"unknown tool: {name}"}
    return fn(**kwargs)


if __name__ == "__main__":
    import json
    print(f"{len(TOOL_DISPATCH)} tools registered:")
    for name in TOOL_DISPATCH:
        print(f"  - {name}")
