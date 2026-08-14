"""JARVIS AGI shim - provides react_agent for WhatsApp bridge.
Uses memory, learning, and tools for improved responses.
"""
import os
import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_FILE = os.path.join(_BASE_DIR, '.env')


def _load_env():
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip())


_load_env()


def _get_api_key(provider: str) -> Optional[str]:
    env_map = {
        'groq': 'GROQ_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY',
        'deepseek': 'DEEPSEEK_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'ollama': 'OLLAMA_API_KEY',
        'moonshot': 'MOONSHOT_API_KEY',
    }
    return os.getenv(env_map.get(provider.lower(), ''))


def _call_groq(message: str, sender: Optional[str] = None, context: str = "", tools_prompt: str = "") -> str:
    api_key = _get_api_key('groq')
    if not api_key:
        return "I'm offline right now. Try again later."
    url = 'https://api.groq.com/openai/v1/chat/completions'
    system_prompt = (
        "You are JARVIS, a helpful assistant on WhatsApp. "
        "Be concise, natural, and human-like. "
        "Keep replies under 300 characters when possible. "
        "Use the conversation history to maintain continuity. "
        "If you don't know something, say so honestly. "
        "Avoid making up facts."
    )
    if context:
        system_prompt += f"\n\nRecent conversation:\n{context}"
    if tools_prompt:
        system_prompt += f"\n\n{tools_prompt}"
    data = json.dumps({
        'model': 'llama-3.3-70b-versatile',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': message}
        ],
        'max_tokens': 500,
        'temperature': 0.7
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as exc:
        return f"Error: {exc}"


def _call_openrouter(message: str, sender: Optional[str] = None, context: str = "", tools_prompt: str = "") -> str:
    api_key = _get_api_key('openrouter')
    if not api_key:
        return "I'm offline right now. Try again later."
    url = 'https://openrouter.ai/api/v1/chat/completions'
    system_prompt = (
        "You are JARVIS, a helpful assistant on WhatsApp. "
        "Be concise, natural, and human-like. "
        "Keep replies under 300 characters when possible. "
        "Use the conversation history to maintain continuity. "
        "If you don't know something, say so honestly. "
        "Avoid making up facts."
    )
    if context:
        system_prompt += f"\n\nRecent conversation:\n{context}"
    if tools_prompt:
        system_prompt += f"\n\n{tools_prompt}"
    data = json.dumps({
        'model': 'google/gemini-2.0-flash-exp:free',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': message}
        ],
        'max_tokens': 500,
        'temperature': 0.7
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://jarvis-bot.local',
        'X-Title': 'JARVIS WhatsApp'
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as exc:
        return f"Error: {exc}"


def react_agent(message: str, sender: Optional[str] = None, context: str = "", tools_prompt: str = "") -> str:
    """Route message to available AI provider with context and tools."""
    if not message or not message.strip():
        return "Say something and I will reply."
    message = message.strip()
    if len(message) > 2000:
        message = message[:2000] + "..."
    for provider in ['groq', 'openrouter']:
        if _get_api_key(provider):
            if provider == 'groq':
                return _call_groq(message, sender, context, tools_prompt)
            if provider == 'openrouter':
                return _call_openrouter(message, sender, context, tools_prompt)
    return "No AI provider configured. Add GROQ_API_KEY or OPENROUTER_API_KEY to .env."
