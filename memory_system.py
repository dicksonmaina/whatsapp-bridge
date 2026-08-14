"""Memory system for JARVIS WhatsApp bot.
Stores conversations, user profiles, and learned patterns.
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

BASE_DIR = Path(__file__).resolve().parent
CONVERSATIONS_DB = BASE_DIR / "conversations.db"
PATTERNS_DB = BASE_DIR / "patterns.db"


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _init_dbs():
    conn = sqlite3.connect(CONVERSATIONS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp)")
    conn.commit()
    conn.close()

    conn = sqlite3.connect(PATTERNS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            pattern_key TEXT NOT NULL,
            pattern_value TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_patterns_unique ON patterns(user_key, pattern_type, pattern_key)")
    conn.commit()
    conn.close()


def save_message(user_key: str, role: str, content: str, metadata: Optional[dict] = None):
    conn = sqlite3.connect(CONVERSATIONS_DB)
    conn.execute(
        "INSERT INTO messages (user_key, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
        (user_key, role, content, _now_iso(), json.dumps(metadata) if metadata else None)
    )
    conn.commit()
    conn.close()


def get_recent_messages(user_key: str, limit: int = 20) -> List[dict]:
    conn = sqlite3.connect(CONVERSATIONS_DB)
    rows = conn.execute(
        "SELECT role, content, timestamp FROM messages WHERE user_key = ? ORDER BY timestamp DESC LIMIT ?",
        (user_key, limit)
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]


def get_context_messages(user_key: str, max_chars: int = 3000) -> List[dict]:
    messages = get_recent_messages(user_key, limit=50)
    context = []
    total = 0
    for msg in reversed(messages):
        text = msg["content"]
        total += len(text)
        if total > max_chars:
            break
        context.append(msg)
    return context


def save_pattern(user_key: str, pattern_type: str, pattern_key: str, pattern_value: Any, confidence: float = 1.0):
    conn = sqlite3.connect(PATTERNS_DB)
    conn.execute(
        """INSERT INTO patterns (user_key, pattern_type, pattern_key, pattern_value, confidence, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_key, pattern_type, pattern_key) DO UPDATE SET
           pattern_value = excluded.pattern_value,
           confidence = excluded.confidence,
           updated_at = excluded.updated_at""",
        (user_key, pattern_type, pattern_key, json.dumps(pattern_value), confidence, _now_iso())
    )
    conn.commit()
    conn.close()


def get_patterns(user_key: str, pattern_type: Optional[str] = None) -> List[dict]:
    conn = sqlite3.connect(PATTERNS_DB)
    if pattern_type:
        rows = conn.execute(
            "SELECT pattern_type, pattern_key, pattern_value, confidence FROM patterns WHERE user_key = ? AND pattern_type = ?",
            (user_key, pattern_type)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT pattern_type, pattern_key, pattern_value, confidence FROM patterns WHERE user_key = ?",
            (user_key,)
        ).fetchall()
    conn.close()
    return [{"type": r[0], "key": r[1], "value": json.loads(r[2]), "confidence": r[3]} for r in rows]


def get_user_summary(user_key: str) -> Dict[str, Any]:
    patterns = get_patterns(user_key)
    summary = {
        "preferences": {},
        "topics": [],
        "style": {},
        "facts": {}
    }
    for p in patterns:
        if p["type"] == "preference":
            summary["preferences"][p["key"]] = p["value"]
        elif p["type"] == "topic":
            summary["topics"].append(p["value"])
        elif p["type"] == "style":
            summary["style"][p["key"]] = p["value"]
        elif p["type"] == "fact":
            summary["facts"][p["key"]] = p["value"]
    return summary


def prune_old_messages(days: int = 30):
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
    conn = sqlite3.connect(CONVERSATIONS_DB)
    conn.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()
