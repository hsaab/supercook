"""Supercook postToolUse hook: log each spawn-tool launch that returned to the run's `launches.jsonl`.

postToolUse fires only after a call succeeds, so a rejected launch is never logged,
and it is not a permission hook, so this script cannot block anything. It logs only
for a live run (see run_folder.run_ledger), never writes through a symlink, and on
any error logs nothing and prints `{}`.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import run_folder

NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)


def returned_agent_id(tool_output: object) -> str | None:
    """The agent id a launch returned: the `agentId` field, else the first id in the raw output."""
    parsed = run_folder.as_dict(tool_output) or {}
    found = run_folder.AGENT_ID.search(str(parsed.get("agentId") or tool_output))
    return found.group(0) if found else None


def row_for(event: dict) -> dict | None:
    call = run_folder.launch_call(event.get("tool_name"), event.get("tool_input"))
    role = run_folder.launch_role(call) if call is not None else None
    if event.get("hook_event_name") != "postToolUse" or role is None:
        return None
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool_use_id": event.get("tool_use_id"),
        "role": role,
        "model": call.get("model"),
        "agent_id": returned_agent_id(event.get("tool_output")),
    }


def append(log: Path, row: dict) -> None:
    descriptor = os.open(log, os.O_WRONLY | os.O_APPEND | os.O_CREAT | NO_FOLLOW, 0o644)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def record(event: dict) -> None:
    row = row_for(event)
    ledger = run_folder.ledger_for(event) if row else None
    if row and ledger:
        append(ledger.parent / run_folder.LAUNCH_LOG, row)


def main() -> None:
    try:
        event = json.loads(sys.stdin.read())
        if isinstance(event, dict):
            record(event)
    except Exception:
        pass
    print("{}", flush=True)


if __name__ == "__main__":
    main()
