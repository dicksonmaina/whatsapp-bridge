#!/usr/bin/env python3
"""Career-Ops Auto-Apply Bot - tracks job applications via SQLite."""
import sqlite3
import os
import re
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "career_ops.db"

JOB_KEYWORDS = [
    "applied", "application", "job", "position", "role", "vacancy",
    "opening", "opportunity", "hiring", "recruiter", "interview",
    "resume", "cv", "cover letter", "linkedin", "indeed", "glassdoor"
]

ACTION_KEYWORDS = [
    "applied", "submitted", "sent", "filed", "dropped", "submitting",
    "applying", "sent application", "applied to", "sent my"
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            sender TEXT NOT NULL,
            platform TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()


def is_job_application(text: str) -> bool:
    text_lower = text.lower()
    has_job = any(kw in text_lower for kw in JOB_KEYWORDS)
    has_action = any(kw in text_lower for kw in ACTION_KEYWORDS)
    return has_job and has_action


def extract_details(text: str) -> tuple[str | None, str | None]:
    text_lower = text.lower()
    patterns = [
        r"(?:applied to|applying for|application for|position of|role of|job as)\s+(.+?)\s+(?:at|with|in|for)\s+([A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,3})",
        r"(.+?)\s+(?:at|with|in)\s+([A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,3})",
        r"([A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,3})\s+(?:at|with|in)\s+([A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,3})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    return None, None


def log_application(job_title: str, company: str, sender: str, platform: str = "whatsapp") -> dict:
    if not job_title or not company:
        raise ValueError("job_title and company are required")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "INSERT INTO applications (job_title, company, applied_at, sender, platform, status) VALUES (?, ?, ?, ?, ?, ?)",
        (job_title, company, datetime.utcnow().isoformat() + "Z", sender, platform, "pending"),
    )
    conn.commit()
    app_id = cursor.lastrowid
    conn.close()
    return {
        "id": app_id,
        "job_title": job_title,
        "company": company,
        "applied_at": datetime.utcnow().isoformat() + "Z",
        "sender": sender,
        "platform": platform,
        "status": "pending",
    }


def recent_applications(limit: int = 5) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, job_title, company, applied_at, sender, platform, status FROM applications ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print("Career-Ops DB initialized at", DB_PATH)
