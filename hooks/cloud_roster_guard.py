"""Supercook project hook: stop followup and Task event log (fails open)."""

from __future__ import annotations

import json
import sys

from cloud_roster_events import print_doctor, record_event
from cloud_roster_ledger import first_open_row, resolve_ledger

FOLLOWUP_RULE = (
    "Launch that worker. With no spawn tool, run it inline per agents.md and "
    "mark the row inline. At a sanctioned pause, mark the row [!] with the blocker."
)


def followup_text(open_row: str) -> str:
    return f"Supercook ledger still has an open roster row:\n{open_row}\n{FOLLOWUP_RULE}"


def _stop_followup(event: dict) -> dict:
    workspace_roots = event.get("workspace_roots")
    if not isinstance(workspace_roots, list):
        return {}
    ledger_path = resolve_ledger([str(item) for item in workspace_roots])
    if ledger_path is None:
        return {}
    open_row = first_open_row(ledger_path.read_text(encoding="utf-8"))
    if open_row is None:
        return {}
    return {"followup_message": followup_text(open_row)}


def main() -> None:
    if sys.argv[1:] == ["doctor"]:
        print_doctor()
        sys.exit(0)

    try:
        event = json.loads(sys.stdin.read())
        if not isinstance(event, dict):
            raise TypeError("event must be an object")
    except Exception:
        print("{}", flush=True)
        sys.exit(0)

    record_event(event)

    result: dict = {}
    if event.get("hook_event_name") == "stop":
        try:
            result = _stop_followup(event)
        except Exception:
            result = {}
    print(json.dumps(result), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
