"""Append-only hook event log and doctor output (stdlib only)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

_PRESENCE_FIELDS = (
    "subagent_type",
    "name",
    "conversation_id",
    "parent_conversation_id",
    "parent_agent_id",
    "parent_tool_call_id",
    "transcript_path",
)
_MAX_LINE = 480
_MAX_LOG_BYTES = 1_048_576


def hook_log_path() -> Path:
    env = os.environ.get("SUPERCOOK_HOOK_LOG")
    if env:
        return Path(env)
    return Path(tempfile.gettempdir()) / "supercook_hook_events.log"


def _present(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def format_event_line(event: dict[str, Any]) -> str:
    event_name = event.get("hook_event_name")
    if not isinstance(event_name, str):
        event_name = "unknown"
    tool = event.get("tool_name")
    tool_bit = tool if isinstance(tool, str) and tool else "-"
    flags = " ".join(
        f"{key}={'yes' if _present(event.get(key)) else 'no'}" for key in _PRESENCE_FIELDS
    )
    line = f"{event_name} tool={tool_bit} {flags}"
    if len(line) > _MAX_LINE:
        return line[: _MAX_LINE - 3] + "..."
    return line


def record_event(event: dict[str, Any]) -> None:
    """Append one capped line; failures must not affect hook output."""
    try:
        path = hook_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and path.stat().st_size > _MAX_LOG_BYTES:
            path.write_text("", encoding="utf-8")
        line = format_event_line(event)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        return


def print_doctor() -> None:
    path = hook_log_path()
    if not path.is_file():
        return
    sys.stdout.write(path.read_text(encoding="utf-8"))
