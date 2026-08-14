#!/usr/bin/env python3
"""Content Repurposing Pipeline - transforms source content into platform-specific variants."""
from dataclasses import dataclass, field
from typing import Optional
import re
import os
import json
from datetime import datetime


@dataclass
class ContentPiece:
    source_text: str
    source_type: str = "generic"
    title: Optional[str] = None


@dataclass
class RepurposedVariant:
    platform: str
    content: str
    char_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def repurpose_twitter(source: ContentPiece) -> RepurposedVariant:
    text = source.source_text.strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    picked = " ".join(sentences[:3])
    picked = _truncate(picked, 280)
    cta = "\n\n#content" if len(picked) < 260 else ""
    return RepurposedVariant(platform="twitter", content=picked + cta, char_count=len(picked) + len(cta))


def repurpose_linkedin(source: ContentPiece) -> RepurposedVariant:
    title = source.title or "New update"
    intro = f"{title}\n\n"
    body = source.source_text.strip()
    body = re.sub(r'\s+', ' ', body)
    content = intro + body
    content = _truncate(content, 3000)
    hashtags = "\n\n#networking #careers #hiring" if len(content) < 2950 else ""
    return RepurposedVariant(platform="linkedin", content=content + hashtags, char_count=len(content) + len(hashtags))


def repurpose_whatsapp(source: ContentPiece) -> RepurposedVariant:
    title = source.title or "Quick update"
    body = _truncate(source.source_text.strip(), 4000)
    content = f"*{title}*\n\n{body}"
    return RepurposedVariant(platform="whatsapp", content=content, char_count=len(content))


def repurpose_summary(source: ContentPiece) -> RepurposedVariant:
    text = source.source_text.strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    summary = " ".join(sentences[: min(5, len(sentences))])
    return RepurposedVariant(platform="summary", content=summary, char_count=len(summary))


_VARIANTS = {
    "twitter": repurpose_twitter,
    "linkedin": repurpose_linkedin,
    "whatsapp": repurpose_whatsapp,
    "summary": repurpose_summary,
}


def repurpose(source: ContentPiece, platforms: list[str] | None = None) -> list[RepurposedVariant]:
    targets = platforms or list(_VARIANTS.keys())
    results = []
    for p in targets:
        fn = _VARIANTS.get(p)
        if fn:
            results.append(fn(source))
    return results


if __name__ == "__main__":
    source = ContentPiece(
        source_text="We just shipped a new feature that cuts onboarding time in half. Clients can now go from signup to first report in under 3 minutes.",
        title="Big update from the team",
    )
    variants = repurpose(source)
    for v in variants:
        print(f"--- {v.platform} ({v.char_count} chars) ---")
        print(v.content)
        print()
