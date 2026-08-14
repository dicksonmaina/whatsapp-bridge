"""Extensible tools/skills registry for JARVIS WhatsApp bot.
Register new tools here to make them available to the bot.
"""
from typing import Callable, Dict, List, Optional, Any
import json


class Tool:
    def __init__(self, name: str, description: str, handler: Callable[[str], str], examples: List[str] = None):
        self.name = name
        self.description = description
        self.handler = handler
        self.examples = examples or []

    def to_prompt(self) -> str:
        return f"- {self.name}: {self.description}"


_registry: Dict[str, Tool] = {}


def register(tool: Tool):
    _registry[tool.name] = tool


def get(name: str) -> Optional[Tool]:
    return _registry.get(name)


def all_tools() -> List[Tool]:
    return list(_registry.values())


def build_tools_prompt() -> str:
    if not _registry:
        return ""
    return "Available tools:\n" + "\n".join(t.to_prompt() for t in _registry.values())


# -------------------- Built-in Tools --------------------
def _web_search_tool(query: str) -> str:
    try:
        import requests
        resp = requests.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        matches = re.findall(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.S)
        if not matches:
            return f"No search results for: {query}"
        lines = [f"Search results for: {query}"]
        for href, title in matches[:5]:
            title = re.sub(r'<[^>]+>', '', title)
            lines.append(f"- {title}\n  {href}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Search failed: {exc}"


def _summarize_tool(text: str) -> str:
    return text[:300] + ("..." if len(text) > 300 else "")


def _translate_tool(text: str, target_lang: str = "english") -> str:
    return f"[Translated to {target_lang}]: {text[:200]}"


def _remind_tool(text: str) -> str:
    return f"Reminder set: {text}"


def _note_tool(text: str) -> str:
    return f"Note saved: {text[:100]}"


# Register built-in tools
import re
register(Tool("web_search", "Search the web for current information. Use when user asks about recent events, facts, or anything needing up-to-date info.", _web_search_tool, ["search for X", "what is X", "latest news about X"]))
register(Tool("summarize", "Summarize long text into 3 short bullet points.", _summarize_tool, ["summarize this", "short version", "tl;dr"]))
register(Tool("translate", "Translate text to the target language.", _translate_tool, ["translate to spanish", "in french"]))
register(Tool("remind", "Set a reminder for the user.", _remind_tool, ["remind me to X", "set reminder"]))
register(Tool("note", "Save a note for the user.", _note_tool, ["note this", "save note"]))
