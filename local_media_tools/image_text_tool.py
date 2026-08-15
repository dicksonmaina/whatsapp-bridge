#!/usr/bin/env python3
"""
image_text_tool.py - Local, free, no-API text extraction from images (OCR).

Requires the tesseract binary on the machine (not just the Python package):
    Debian/Kali/Mint:  sudo apt install tesseract-ocr
    (optional extra languages: tesseract-ocr-eng, tesseract-ocr-swa, etc.)

Everything else runs 100% offline — no vision API, no billing.

Import and call directly:
    from image_text_tool import extract_text
    result = extract_text("/path/to/screenshot.png")
"""

import os
from PIL import Image, ImageOps, ImageFilter

try:
    import pytesseract
except ImportError:
    pytesseract = None


def _preprocess(img: Image.Image) -> Image.Image:
    """Light cleanup to improve OCR accuracy on screenshots/photos."""
    img = img.convert("L")  # grayscale
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.SHARPEN)
    return img


def extract_text(path: str, lang: str = "eng", preprocess: bool = True) -> dict:
    """
    Extract text from an image via OCR. Returns a plain dict —
    safe to json.dumps() straight back to an LLM as a tool result.
    """
    if pytesseract is None:
        return {"error": "pytesseract not installed. Run: pip install pytesseract --break-system-packages"}

    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    try:
        img = Image.open(path)
    except Exception as e:
        return {"error": f"could not open image: {e}"}

    proc_img = _preprocess(img) if preprocess else img

    try:
        text = pytesseract.image_to_string(proc_img, lang=lang)
    except pytesseract.TesseractNotFoundError:
        return {
            "error": "tesseract binary not installed on this machine. "
                     "Run: sudo apt install tesseract-ocr"
        }
    except Exception as e:
        return {"error": f"OCR failed: {e}"}

    text = text.strip()

    return {
        "file": os.path.basename(path),
        "lang": lang,
        "text": text,
        "char_count": len(text),
        "line_count": len(text.splitlines()) if text else 0,
        "found_text": bool(text),
    }


def extract_text_detailed(path: str, lang: str = "eng") -> dict:
    """
    Extract text plus per-word confidence and bounding boxes.
    Useful if you need to know WHERE on the image text sits.
    """
    if pytesseract is None:
        return {"error": "pytesseract not installed. Run: pip install pytesseract --break-system-packages"}

    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    img = _preprocess(Image.open(path))

    try:
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError:
        return {"error": "tesseract binary not installed. Run: sudo apt install tesseract-ocr"}

    words = []
    for i, word in enumerate(data["text"]):
        if word.strip():
            words.append({
                "text": word,
                "confidence": data["conf"][i],
                "box": {
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                },
            })

    return {"file": os.path.basename(path), "word_count": len(words), "words": words}


# ── LLM tool-calling schema (OpenAI/Groq/Ollama function-call format) ──

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "extract_text",
            "description": (
                "Extract readable text from a local image file via OCR "
                "(screenshots, photos of documents, signs, etc). Free, "
                "local, no API calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the image file",
                    },
                    "lang": {
                        "type": "string",
                        "description": "Tesseract language code, e.g. 'eng'. Default 'eng'.",
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
        print("Usage: python3 image_text_tool.py <image_path> [lang]")
        sys.exit(1)
    lang = sys.argv[2] if len(sys.argv) > 2 else "eng"
    print(json.dumps(extract_text(sys.argv[1], lang=lang), indent=2))
