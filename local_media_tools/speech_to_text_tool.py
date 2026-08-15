#!/usr/bin/env python3
"""
speech_to_text_tool.py - Local, free speech-to-text via OpenAI Whisper
(the open-source model, run locally — NOT the paid OpenAI API).

One-time setup:
    sudo apt install ffmpeg   # already required by JARVIS media handling
    pip install openai-whisper --break-system-packages
    # first run auto-downloads the chosen model size, then fully offline.

Model size vs speed/accuracy tradeoff (pick based on your hardware):
    tiny   ~75MB   fastest, roughest
    base   ~150MB  good default for a Kali/Mint box
    small  ~500MB  better accuracy, slower
"""

import os

try:
    import whisper
except ImportError:
    whisper = None

_model_cache = {}


def _get_model(size: str = "base"):
    if size not in _model_cache:
        _model_cache[size] = whisper.load_model(size)
    return _model_cache[size]


def transcribe_audio(path: str, model_size: str = "base", language: str = None) -> dict:
    """
    Transcribe speech from a local audio/video file. Returns a plain dict.
    Accepts anything ffmpeg can read (mp3, wav, m4a, ogg, mp4, etc).
    """
    if whisper is None:
        return {"error": "openai-whisper not installed. Run: pip install openai-whisper --break-system-packages"}

    if not os.path.exists(path):
        return {"error": f"file not found: {path}"}

    model = _get_model(model_size)
    result = model.transcribe(path, language=language)

    segments = [
        {"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
        for s in result.get("segments", [])
    ]

    return {
        "file": os.path.basename(path),
        "detected_language": result.get("language"),
        "text": result.get("text", "").strip(),
        "segments": segments,
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "transcribe_audio",
            "description": (
                "Transcribe speech from a local audio or video file (voice "
                "notes, calls, videos) to text. Free, local, no API calls "
                "after first-time model download."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the audio/video file"},
                    "language": {"type": "string", "description": "Optional ISO language code, e.g. 'en'"},
                },
                "required": ["path"],
            },
        },
    },
]


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python3 speech_to_text_tool.py <audio_path>")
        sys.exit(1)
    print(json.dumps(transcribe_audio(sys.argv[1]), indent=2))
