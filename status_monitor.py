#!/usr/bin/env python3
"""Status / Monitoring Bot - checks service, port and system health."""
from __future__ import annotations

import os
import socket
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, UTC


@dataclass
class StatusCheck:
    name: str
    ok: bool
    detail: str = ""
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def check_port(host: str, port: int, timeout: float = 1.0) -> StatusCheck:
    name = f"port {host}:{port}"
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return StatusCheck(name=name, ok=True, detail="open")
    except (OSError, socket.timeout):
        return StatusCheck(name=name, ok=False, detail="closed")


def check_service(name: str) -> StatusCheck:
    try:
        out = subprocess.check_output(
            ["sc", "query", name], stderr=subprocess.STDOUT, text=True, shell=False
        )
        running = "RUNNING" in out.upper()
        return StatusCheck(name=f"service {name}", ok=running, detail="running" if running else "not-running")
    except subprocess.CalledProcessError as exc:
        return StatusCheck(name=f"service {name}", ok=False, detail=exc.output.strip())


def check_process(name: str) -> StatusCheck:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {name}"], stderr=subprocess.STDOUT, text=True, shell=False
        )
        found = name.lower() in out.lower()
        return StatusCheck(name=f"process {name}", ok=found, detail="found" if found else "not-found")
    except subprocess.CalledProcessError as exc:
        return StatusCheck(name=f"process {name}", ok=False, detail=exc.output.strip())


def check_disk(path: str = "C:\\") -> StatusCheck:
    usage = shutil.disk_usage(path)
    pct = usage.used / usage.total * 100
    ok = pct < 90
    return StatusCheck(
        name=f"disk {path}",
        ok=ok,
        detail=f"{pct:.1f}% used",
    )


def run_checks(checks: list[dict]) -> list[StatusCheck]:
    results: list[StatusCheck] = []
    for c in checks:
        kind = c.get("type")
        if kind == "port":
            results.append(check_port(c.get("host", "127.0.0.1"), int(c.get("port", 0))))
        elif kind == "service":
            results.append(check_service(c["name"]))
        elif kind == "process":
            results.append(check_process(c["name"]))
        elif kind == "disk":
            results.append(check_disk(c.get("path", "C:\\")))
    return results


def summarize(results: list[StatusCheck]) -> str:
    lines = ["Status Monitor Report:", ""]
    for r in results:
        marker = "PASS" if r.ok else "FAIL"
        lines.append(f"[{marker}] {r.name}: {r.detail}")
    failed = sum(1 for r in results if not r.ok)
    lines.append("")
    lines.append(f"Result: {len(results) - failed}/{len(results)} checks passed")
    return "\n".join(lines)


if __name__ == "__main__":
    checks = [
        {"type": "port", "host": "127.0.0.1", "port": 5051},
        {"type": "port", "host": "127.0.0.1", "port": 5057},
        {"type": "port", "host": "127.0.0.1", "port": 18789},
        {"type": "service", "name": "FlaskHandler"},
        {"type": "service", "name": "JarvisAGI"},
        {"type": "service", "name": "OpenClawGateway"},
        {"type": "process", "name": "node.exe"},
        {"type": "disk", "path": "C:\\"},
    ]
    results = run_checks(checks)
    print(summarize(results))
