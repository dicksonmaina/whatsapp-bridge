#!/usr/bin/env python3
"""Client Intake Bot - collects prospective client information via conversational flow."""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, UTC


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_intake.db")


@dataclass
class ClientLead:
    name: str = ""
    email: str = ""
    company: str = ""
    project_type: str = ""
    budget_range: str = ""
    timeline: str = ""
    notes: str = ""
    status: str = "new"
    source: str = "whatsapp"
    sender: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


_INTAKE_FLOW = ["name", "email", "company", "project_type", "budget_range", "timeline"]
_QUESTIONS = {
    "name": "What is your full name?",
    "email": "What is your email address?",
    "company": "Which company or organization are you with?",
    "project_type": "What type of project are you looking for? (e.g., web app, automation, consulting)",
    "budget_range": "Do you have a rough budget range in mind?",
    "timeline": "When do you need this delivered by?",
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS client_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            company TEXT,
            project_type TEXT,
            budget_range TEXT,
            timeline TEXT,
            notes TEXT,
            status TEXT,
            source TEXT,
            sender TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def _save_lead(lead: ClientLead):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO client_leads
            (name, email, company, project_type, budget_range, timeline, notes, status, source, sender, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead.name,
            lead.email,
            lead.company,
            lead.project_type,
            lead.budget_range,
            lead.timeline,
            lead.notes,
            lead.status,
            lead.source,
            lead.sender,
            lead.created_at,
        ),
    )
    conn.commit()
    conn.close()


def _current_step(state: dict) -> str:
    for step in _INTAKE_FLOW:
        if not state.get(step):
            return step
    return "done"


def handle_intake(message: str, sender: str) -> str:
    state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"intake_state_{sender or 'anon'}.json")
    state: dict = {}
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

    step = _current_step(state)
    if step == "done":
        os.remove(state_file, ignore_errors=True)
        return "Thank you! Your intake details are already captured. I'll connect you with the team shortly."

    state[step] = message.strip()
    next_step = _current_step(state)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)

    if next_step == "done":
        lead = ClientLead(
            name=state.get("name", ""),
            email=state.get("email", ""),
            company=state.get("company", ""),
            project_type=state.get("project_type", ""),
            budget_range=state.get("budget_range", ""),
            timeline=state.get("timeline", ""),
            notes="",
            status="new",
            source="whatsapp",
            sender=sender or "unknown",
        )
        _save_lead(lead)
        os.remove(state_file, ignore_errors=True)
        return (
            f"Thanks {lead.name}. I logged your request for {lead.project_type} ({lead.timeline})."
            f" Someone will reach out to {lead.email} soon."
        )

    return _QUESTIONS[next_step]


def is_intake_message(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in ["start intake", "new client", "client intake", "onboard", "get started", "quote"])


if __name__ == "__main__":
    init_db()
    print("Client intake DB initialized at", DB_PATH)
    print("Test:", handle_intake("Riziki", "test-user"))
    print("Next:", handle_intake("riziki@example.com", "test-user"))
