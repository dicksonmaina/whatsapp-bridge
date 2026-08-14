from flask import Flask, request, jsonify
import sys
import os
import json
import sqlite3
import re
import hashlib
import time
import requests as http_requests
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import career_ops_bot as career
from memory_system import (
    save_message, get_recent_messages, get_context_messages,
    get_user_summary, save_pattern, get_patterns, _init_dbs as _init_memory_dbs, _now_iso
)
from learning_engine import analyze_user, build_adaptive_prompt, get_conversation_context
from tools_registry import build_tools_prompt, all_tools, get as get_tool

JARVIS_AGI_URL = os.getenv('JARVIS_AGI_URL', 'http://127.0.0.1:5052/agent')
BOT_PORT = 5056
for i, arg in enumerate(sys.argv):
    if arg == '--port' and i + 1 < len(sys.argv):
        BOT_PORT = int(sys.argv[i + 1])

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
NOTES_DB = BASE_DIR / "notes.db"
REMINDERS_DB = BASE_DIR / "reminders.db"
USERS_DB = BASE_DIR / "users.db"

_conversation_state: Dict[str, dict] = {}
_user_profiles: Dict[str, dict] = {}
_pending_flows: Dict[str, dict] = {}
_request_times: Dict[str, List[float]] = {}


def _state_key(sender: str) -> str:
    return sender or "anonymous"


def _get_user_profile(user_key: str) -> dict:
    if user_key in _user_profiles:
        return _user_profiles[user_key]
    conn = sqlite3.connect(USERS_DB)
    row = conn.execute("SELECT user_key, name, phone, timezone, preferences, first_seen, last_seen FROM users WHERE user_key = ?", (user_key,)).fetchone()
    conn.close()
    if row:
        profile = {
            "user_key": row[0], "name": row[1], "phone": row[2],
            "timezone": row[3] or "UTC", "preferences": json.loads(row[4] or "{}"),
            "first_seen": row[5], "last_seen": row[6],
        }
    else:
        profile = {
            "user_key": user_key, "name": None, "phone": user_key,
            "timezone": "UTC", "preferences": {},
            "first_seen": _now_iso(), "last_seen": _now_iso(),
        }
        conn = sqlite3.connect(USERS_DB)
        conn.execute("INSERT INTO users (user_key, phone, first_seen, last_seen) VALUES (?, ?, ?, ?)",
                     (user_key, user_key, profile["first_seen"], profile["last_seen"]))
        conn.commit()
        conn.close()
    _user_profiles[user_key] = profile
    return profile


def _update_last_seen(user_key: str):
    conn = sqlite3.connect(USERS_DB)
    conn.execute("UPDATE users SET last_seen = ? WHERE user_key = ?", (_now_iso(), user_key))
    conn.commit()
    conn.close()
    if user_key in _user_profiles:
        _user_profiles[user_key]["last_seen"] = _now_iso()


def _remember_name(user_key: str, name: str):
    conn = sqlite3.connect(USERS_DB)
    conn.execute("UPDATE users SET name = ? WHERE user_key = ?", (name, user_key))
    conn.commit()
    conn.close()
    if user_key in _user_profiles:
        _user_profiles[user_key]["name"] = name
    save_pattern(user_key, "preference", "user_name", name, confidence=0.9)


def _get_user_name(user_key: str) -> str:
    profile = _get_user_profile(user_key)
    if profile.get("name"):
        return profile["name"]
    if user_key and "@" in user_key:
        return user_key.split("@")[0]
    return "friend"


def _save_note(user_key: str, title: str, body: str, tags: str = ""):
    conn = sqlite3.connect(NOTES_DB)
    conn.execute("INSERT INTO notes (user_key, title, body, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (user_key, title, body, tags, _now_iso(), _now_iso()))
    conn.commit()
    note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    save_pattern(user_key, "topic", "notes", "used_notes", confidence=0.5)
    return note_id


def _list_notes(user_key: str, limit: int = 10):
    conn = sqlite3.connect(NOTES_DB)
    rows = conn.execute("SELECT id, title, body, tags, created_at FROM notes WHERE user_key = ? ORDER BY created_at DESC LIMIT ?", (user_key, limit)).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "body": r[2], "tags": r[3], "created_at": r[4]} for r in rows]


def _add_reminder(user_key: str, text: str, due_at: str):
    conn = sqlite3.connect(REMINDERS_DB)
    conn.execute("INSERT INTO reminders (user_key, text, due_at, created_at) VALUES (?, ?, ?, ?)", (user_key, text, due_at, _now_iso()))
    conn.commit()
    rem_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    save_pattern(user_key, "topic", "reminders", "used_reminders", confidence=0.5)
    return rem_id


def _rate_limit(user_key: str, max_per_minute: int = 20) -> bool:
    now = time.time()
    window = 60
    times = _request_times.get(user_key, [])
    times = [t for t in times if now - t < window]
    _request_times[user_key] = times
    if len(times) >= max_per_minute:
        return True
    times.append(now)
    _request_times[user_key] = times
    return False


COMMANDS = {
    "/start": "Welcome, {name}. I am JARVIS on WhatsApp. I learn from our chats and get better over time. Use /help to see what I can do.",
    "/help": """Commands:
/start - Welcome message
/help - This menu
/status - System health
/jobs - Recent applications
/leads - Recent client leads
/notes - Manage notes
/remind - Set reminders
/search <query> - Web search
/summarize <text> - Summarize text
/translate <lang> <text> - Translate text
/clear - Clear my data
/name <your name> - Tell me your name""",
}


def _handle_command(message: str, sender: str) -> str:
    user_key = _state_key(sender)
    name = _get_user_name(user_key)
    text = message.strip()
    lowered = text.lower()

    if lowered.startswith("/start"):
        _update_last_seen(user_key)
        return COMMANDS["/start"].format(name=name)

    if lowered.startswith("/help"):
        _update_last_seen(user_key)
        return COMMANDS["/help"]

    if lowered.startswith("/name "):
        new_name = text[6:].strip()
        if new_name:
            _remember_name(user_key, new_name)
            return f"Got it, {new_name}. I will use that from now on."
        return "Please tell me your name like this: /name Richie"

    if lowered.startswith("/status"):
        _update_last_seen(user_key)
        try:
            checks = []
            try:
                checks.append(("Flask", http_requests.get(f"http://localhost:{BOT_PORT}/health", timeout=2).status_code == 200))
            except Exception:
                checks.append(("Flask", False))
            try:
                checks.append(("Send API", http_requests.get("http://localhost:5057/health", timeout=2).status_code == 200))
            except Exception:
                checks.append(("Send API", False))
            lines = ["System Status"]
            for svc, ok in checks:
                lines.append(f"{'PASS' if ok else 'FAIL'} {svc}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Could not check status: {exc}"

    if lowered.startswith("/jobs"):
        _update_last_seen(user_key)
        try:
            entries = career.recent_applications(limit=5)
            if not entries:
                return "No job applications logged yet."
            lines = ["Recent Applications"]
            for e in entries:
                lines.append(f"#{e['id']}: {e['job_title']} at {e['company']} ({e['status']})")
            return "\n".join(lines)
        except Exception as exc:
            return f"Could not load jobs: {exc}"

    if lowered.startswith("/leads"):
        _update_last_seen(user_key)
        try:
            import client_intake_bot as intake
            rows = intake.recent_leads(limit=5)
            if not rows:
                return "No client leads captured yet."
            lines = ["Recent Leads"]
            for r in rows:
                lines.append(f"{r.get('name','?')} | {r.get('company','?')} | {r.get('project_type','?')} | {r.get('status','new')}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Could not load leads: {exc}"

    if lowered.startswith("/notes"):
        _update_last_seen(user_key)
        args = text[7:].strip().lower()
        if not args:
            notes = _list_notes(user_key)
            if not notes:
                return "No notes yet. Use /notes add <title> | <body> or /notes save <body>"
            lines = ["Your Notes"]
            for n in notes[:10]:
                title = n["title"] or "Untitled"
                lines.append(f"- {title} ({n['id']})")
            return "\n".join(lines)
        if args.startswith("add "):
            rest = text[11:].strip()
            if "|" in rest:
                title, body = rest.split("|", 1)
                title = title.strip()
                body = body.strip()
            else:
                title = _now_iso()
                body = rest
            note_id = _save_note(user_key, title, body)
            return f"Saved note #{note_id}: {title}"
        if args.startswith("save "):
            body = text[11:].strip()
            note_id = _save_note(user_key, None, body)
            return f"Saved quick note #{note_id}."
        return "Usage: /notes | /notes add <title> | <body> | /notes save <body>"

    if lowered.startswith("/remind "):
        _update_last_seen(user_key)
        body = text[8:].strip()
        m = re.match(r"(.+?)\s+(?:in\s+(\d+)\s*(m|min|minutes?|h|hr|hours?|d|days?)|at\s+([0-9:]+))", body, re.IGNORECASE)
        if not m:
            return "Usage: /remind <text> in <n> min|hours|days OR /remind <text> at HH:MM"
        reminder_text = m.group(1).strip()
        unit = (m.group(3) or "m").lower()
        value = int(m.group(2) or 1)
        if unit.startswith("h"):
            due = datetime.utcnow() + timedelta(hours=value)
        elif unit.startswith("d"):
            due = datetime.utcnow() + timedelta(days=value)
        else:
            due = datetime.utcnow() + timedelta(minutes=value)
        due_at = due.isoformat() + "Z"
        rem_id = _add_reminder(user_key, reminder_text, due_at)
        return f"Reminder #{rem_id} set: '{reminder_text}' due {due.strftime('%Y-%m-%d %H:%M UTC')}"

    if lowered.startswith("/search "):
        query = text[8:].strip()
        if not query:
            return "Usage: /search <query>"
        tool = get_tool("web_search")
        if tool:
            return tool.handler(query)
        return "Search tool not available."

    if lowered.startswith("/summarize "):
        text = text[11:].strip()
        if not text:
            return "Usage: /summarize <text>"
        if len(text) < 200:
            return text
        tool = get_tool("summarize")
        if tool:
            return tool.handler(text)
        return text[:300]

    if lowered.startswith("/translate "):
        parts = text[11:].strip().split(" ", 1)
        if len(parts) < 2:
            return "Usage: /translate <lang> <text>"
        lang = parts[0].lower()
        content = parts[1]
        tool = get_tool("translate")
        if tool:
            return tool.handler(content, lang)
        return f"[Translation to {lang}]: {content[:200]}"

    if lowered.startswith("/clear"):
        _conversation_state.pop(user_key, None)
        _pending_flows.pop(user_key, None)
        return "Cleared your session."

    return None


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    message = data.get('message', '') or ''
    sender = data.get('sender', '') or ''
    if not message:
        return jsonify({'reply': 'Empty message received.'}), 400

    user_key = _state_key(sender)
    _update_last_seen(user_key)
    name = _get_user_name(user_key)

    if _rate_limit(user_key):
        return jsonify({'reply': "You're sending messages too quickly. Please wait a moment."})

    if message.startswith('/'):
        cmd_reply = _handle_command(message, sender)
        if cmd_reply is not None:
            save_message(user_key, "user", message)
            save_message(user_key, "assistant", cmd_reply)
            return jsonify({'reply': cmd_reply})

    flow = _pending_flows.get(user_key)
    if flow:
        flow_type = flow.get('type')
        if flow_type == 'note_title':
            flow['title'] = message.strip()
            flow['step'] = 'body'
            _pending_flows[user_key] = flow
            save_message(user_key, "user", message)
            return jsonify({'reply': 'What should the note say?'})
        if flow_type == 'note_body':
            title = flow.get('title') or 'Untitled'
            note_id = _save_note(user_key, title, message.strip())
            _pending_flows.pop(user_key, None)
            save_message(user_key, "user", message)
            reply = f"Saved note #{note_id}: {title}"
            save_message(user_key, "assistant", reply)
            return jsonify({'reply': reply})
        if flow_type == 'reminder_text':
            flow['text'] = message.strip()
            flow['step'] = 'when'
            _pending_flows[user_key] = flow
            save_message(user_key, "user", message)
            return jsonify({'reply': f'Remind you about: {flow["text"]}\nWhen?'})
        if flow_type == 'reminder_when':
            body = flow.get('text', '')
            when = message.strip()
            due_at = None
            m = re.match(r"(?:in\s+)?(\d+)\s*(m|min|minutes?|h|hr|hours?|d|days?)", when, re.IGNORECASE)
            if m:
                value = int(m.group(1))
                unit = m.group(2).lower()
                if unit.startswith("h"):
                    due = datetime.utcnow() + timedelta(hours=value)
                elif unit.startswith("d"):
                    due = datetime.utcnow() + timedelta(days=value)
                else:
                    due = datetime.utcnow() + timedelta(minutes=value)
                due_at = due.isoformat() + "Z"
            else:
                try:
                    now = datetime.utcnow()
                    due = datetime.strptime(when, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
                    if due < now:
                        due += timedelta(days=1)
                    due_at = due.isoformat() + "Z"
                except ValueError:
                    pass
            _pending_flows.pop(user_key, None)
            save_message(user_key, "user", message)
            if due_at:
                rem_id = _add_reminder(user_key, body, due_at)
                reply = f"Reminder #{rem_id} set: '{body}'"
                save_message(user_key, "assistant", reply)
                return jsonify({'reply': reply})
            reply = "I didn't catch that time. Try: in 15 min, in 2 hours, or at 14:30"
            save_message(user_key, "assistant", reply)
            return jsonify({'reply': reply})

    if message.lower().startswith("note "):
        _pending_flows[user_key] = {'type': 'note_title', 'step': 'title'}
        save_message(user_key, "user", message)
        return jsonify({'reply': 'What should I title this note?'})

    if message.lower().startswith("remind "):
        text = message[7:].strip()
        _pending_flows[user_key] = {'type': 'reminder_text', 'step': 'text', 'text': text}
        save_message(user_key, "user", message)
        return jsonify({'reply': f'Remind you about: {text}\nWhen?'})

    state = _conversation_state.get(user_key, {})

    if state.get('awaiting_job_details'):
        job_title = state.get('job_title')
        company = state.get('company')
        if not job_title:
            job_title = message.strip()
        if not company:
            company = message.strip()
        if job_title and company:
            entry = career.log_application(
                job_title=job_title,
                company=company,
                sender=sender or 'unknown',
                platform='whatsapp',
            )
            _conversation_state.pop(user_key, None)
            save_message(user_key, "user", message)
            reply = (
                f"Logged application #{entry['id']}: "
                f"{entry['job_title']} at {entry['company']} "
                f"({entry['status']})"
            )
            save_message(user_key, "assistant", reply)
            return jsonify({'reply': reply})
        _conversation_state[user_key] = {
            'awaiting_job_details': True,
            'job_title': job_title,
            'company': company,
            'missing': 'job_title' if not job_title else 'company',
        }
        save_message(user_key, "user", message)
        if not job_title:
            reply = "What job title did you apply for?"
            save_message(user_key, "assistant", reply)
            return jsonify({'reply': reply})
        if not company:
            reply = f"What company is the {job_title} role at?"
            save_message(user_key, "assistant", reply)
            return jsonify({'reply': reply})

    if career.is_job_application(message):
        job_title, company = career.extract_details(message)
        if job_title and company:
            entry = career.log_application(
                job_title=job_title,
                company=company,
                sender=sender or 'unknown',
                platform='whatsapp',
            )
            save_message(user_key, "user", message)
            reply = (
                f"Logged application #{entry['id']}: "
                f"{entry['job_title']} at {entry['company']} "
                f"({entry['status']})"
            )
            save_message(user_key, "assistant", reply)
            return jsonify({'reply': reply})
        _conversation_state[user_key] = {
            'awaiting_job_details': True,
            'job_title': job_title,
            'company': company,
            'missing': None,
        }
        save_message(user_key, "user", message)
        if job_title and not company:
            reply = f"What company is the {job_title} role at?"
            save_message(user_key, "assistant", reply)
            return jsonify({'reply': reply})
        if company and not job_title:
            reply = f"What job title at {company} did you apply for?"
            save_message(user_key, "assistant", reply)
            return jsonify({'reply': reply})
        reply = "I caught an application mention, but I need both the job title and company. What job did you apply for and where?"
        save_message(user_key, "assistant", reply)
        return jsonify({'reply': reply})

    try:
        save_message(user_key, "user", message)
        context = get_conversation_context(user_key, max_chars=2500)
        adaptive_prompt = build_adaptive_prompt(user_key)
        tools_prompt = build_tools_prompt()
        payload = {
            'query': message,
            'sender': sender,
            'context': context,
            'system_prompt': adaptive_prompt,
            'tools': tools_prompt
        }
        resp = http_requests.post(JARVIS_AGI_URL, json=payload, timeout=60)
        data = resp.json()
        reply = data.get('reply') or data.get('response') or "No response from brain."
        save_message(user_key, "assistant", reply)
        return jsonify({'reply': reply})
    except Exception as exc:
        return jsonify({'reply': "Brain error. Please try again in a moment."})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': _now_iso()})


@app.route('/buttons', methods=['POST'])
def buttons():
    data = request.get_json(force=True)
    to = data.get('to')
    text = data.get('text', 'Choose an option:')
    buttons = data.get('buttons', [])
    if not to or not buttons:
        return jsonify({'error': 'to and buttons are required'}), 400
    formatted = []
    for b in buttons[:3]:
        formatted.append({
            'buttonText': {'displayText': b},
            'buttonParams': {'id': b, 'command_params': b}
        })
    payload = {
        'to': to,
        'text': text,
        'buttons': formatted,
        'headerType': 1
    }
    try:
        resp = http_requests.post(f"http://localhost:5057/sendButtons", json=payload, timeout=10)
        return jsonify(resp.json())
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    _init_memory_dbs()
    conn = sqlite3.connect(NOTES_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            title TEXT,
            body TEXT NOT NULL,
            tags TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_key)")
    conn.commit()
    conn.close()
    conn = sqlite3.connect(REMINDERS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            text TEXT NOT NULL,
            due_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_key)")
    conn.commit()
    conn.close()
    conn = sqlite3.connect(USERS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_key TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            timezone TEXT DEFAULT 'UTC',
            preferences TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    app.run(host='0.0.0.0', port=BOT_PORT, debug=False)
