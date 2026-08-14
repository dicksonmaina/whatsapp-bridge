"""Learning engine for JARVIS WhatsApp bot.
Analyzes conversations to extract patterns and improve responses over time.
"""
import json
import re
from typing import List, Dict, Any, Optional
from memory_system import get_recent_messages, get_context_messages, get_user_summary, save_pattern, get_patterns


def extract_preferences(user_key: str, messages: List[dict]):
    for msg in messages:
        content = msg.get("content", "").lower()
        role = msg.get("role", "")
        if role == "user":
            if "my name is" in content or "i am " in content or "i'm " in content:
                name = re.sub(r"(?:my name is|i am|i'm)\s+", "", content).strip().split()[0] if content.split() else None
                if name:
                    save_pattern(user_key, "preference", "user_name", name, confidence=0.9)
            if "don't like" in content or "i hate" in content or "i dislike" in content:
                pref = re.sub(r"(?:don't like|i hate|i dislike)\s+", "", content).strip().split()[:3]
                if pref:
                    save_pattern(user_key, "preference", "dislikes", " ".join(pref), confidence=0.7)
            if "i love" in content or "i like" in content or "my favorite" in content:
                pref = re.sub(r"(?:i love|i like|my favorite)\s+", "", content).strip().split()[:3]
                if pref:
                    save_pattern(user_key, "preference", "likes", " ".join(pref), confidence=0.7)
            if "call me" in content:
                name = content.split("call me")[-1].strip().split()[0] if "call me" in content else None
                if name:
                    save_pattern(user_key, "preference", "user_name", name, confidence=0.9)


def extract_topics(user_key: str, messages: List[dict]):
    topics = []
    keywords = ["job", "career", "project", "business", "client", "lead", "reminder", "note", "search", "translate", "summarize"]
    for msg in messages:
        content = msg.get("content", "").lower()
        for kw in keywords:
            if kw in content and kw not in topics:
                topics.append(kw)
    for topic in topics[:10]:
        save_pattern(user_key, "topic", "mentioned", topic, confidence=0.6)


def extract_style(user_key: str, messages: List[dict]):
    user_msgs = [m for m in messages if m.get("role") == "user"]
    if len(user_msgs) < 3:
        return
    avg_len = sum(len(m.get("content", "")) for m in user_msgs) / len(user_msgs)
    save_pattern(user_key, "style", "avg_message_length", round(avg_len, 1), confidence=0.5)
    formal = any(m.get("content", "").lower().startswith(("please", "kindly", "would you", "could you")) for m in user_msgs)
    save_pattern(user_key, "style", "formal", "yes" if formal else "no", confidence=0.6)
    emoji_count = sum(1 for m in user_msgs if any(ord(c) > 0x1F600 for c in m.get("content", "")))
    save_pattern(user_key, "style", "uses_emoji", "yes" if emoji_count / len(user_msgs) > 0.3 else "no", confidence=0.6)


def extract_facts(user_key: str, messages: List[dict]):
    for msg in messages:
        content = msg.get("content", "")
        if msg.get("role") == "user":
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
            for email in emails:
                save_pattern(user_key, "fact", "email", email, confidence=0.8)
            phones = re.findall(r"\+?\d{10,15}", content)
            for phone in phones:
                save_pattern(user_key, "fact", "phone", phone, confidence=0.7)


def analyze_user(user_key: str):
    messages = get_recent_messages(user_key, limit=100)
    if not messages:
        return
    extract_preferences(user_key, messages)
    extract_topics(user_key, messages)
    extract_style(user_key, messages)
    extract_facts(user_key, messages)


def build_adaptive_prompt(user_key: str, base_prompt: str = "You are JARVIS, a helpful assistant on WhatsApp.") -> str:
    summary = get_user_summary(user_key)
    parts = [base_prompt]
    if summary.get("preferences", {}).get("user_name"):
        parts.append(f"The user's name is {summary['preferences']['user_name']}. Use it naturally.")
    if summary.get("style", {}).get("formal") == "yes":
        parts.append("The user prefers formal communication. Be polite and professional.")
    if summary.get("style", {}).get("formal") == "no":
        parts.append("The user prefers casual communication. Be relaxed and natural.")
    if summary.get("style", {}).get("uses_emoji") == "yes":
        parts.append("The user uses emojis. Match their tone with appropriate emojis.")
    if summary.get("topics"):
        topics = list(set(summary["topics"]))[:5]
        parts.append(f"The user often talks about: {', '.join(topics)}.")
    if summary.get("facts", {}).get("email"):
        parts.append(f"The user's email is {summary['facts']['email']}.")
    parts.append("Keep replies concise, natural, and human-like. Avoid robotic phrases.")
    return " ".join(parts)


def get_conversation_context(user_key: str, max_messages: int = 10, max_chars: int = 2500) -> str:
    messages = get_context_messages(user_key, max_chars=max_chars)
    if not messages:
        return ""
    lines = []
    for m in messages[-max_messages:]:
        role = m.get("role", "user")
        content = m.get("content", "")
        prefix = "User" if role == "user" else "JARVIS"
        lines.append(f"{prefix}: {content}")
    return "\n".join(lines)
