#!/usr/bin/env python3
"""
pdf_text_tool.py - Local, free PDF text extraction.
Pure Python (pypdf), no API, no billing.

One-time setup:
    pip install pypdf --break-system-packages
"""

import os

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def extract_pdf_text(path: str, max_pages: int = None) -> dict:
    """
    Extract text from a PDF, page by page. Returns a plain dict.
    """
    if PdfReader is None:
        return {"error": "pypdf not installed. Run: pip install pypdf --break-system-packages"}

    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    try:
        reader = PdfReader(path)
    except Exception as e:
        return {"error": f"could not open PDF: {e}"}

    total_pages = len(reader.pages)
    pages_to_read = total_pages if max_pages is None else min(max_pages, total_pages)

    pages = []
    full_text_parts = []
    for i in range(pages_to_read):
        text = reader.pages[i].extract_text() or ""
        pages.append({"page": i + 1, "text": text.strip()})
        full_text_parts.append(text)

    full_text = "\n".join(full_text_parts).strip()

    return {
        "file": os.path.basename(path),
        "total_pages": total_pages,
        "pages_read": pages_to_read,
        "text": full_text,
        "char_count": len(full_text),
        "pages": pages,
        "encrypted": reader.is_encrypted,
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "extract_pdf_text",
            "description": (
                "Extract text content from a local PDF file, page by page. "
                "Free, local, no API calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the PDF file"},
                    "max_pages": {"type": "integer", "description": "Optional cap on pages read"},
                },
                "required": ["path"],
            },
        },
    },
]


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python3 pdf_text_tool.py <pdf_path>")
        sys.exit(1)
    print(json.dumps(extract_pdf_text(sys.argv[1]), indent=2))
