"""Supercook stop hook: nudge the parent about worker steps the ledger and launch log disagree on.

Reads the live run's `ledger.md` and `launches.jsonl` and returns what
run_folder.problems found as a followup message, citing each step by number. It never
denies anything, does nothing without a live run or when the user aborted, and on any
error prints `{}`.
"""

from __future__ import annotations

import json
import sys

import run_folder

FOLLOWUP_RULE = (
    "Launch the worker with the spawn tool. Run a step inline per references/workers.md "
    "(solo mode) only when no spawn tool is listed, and mark it inline. At a sanctioned "
    "pause, mark the step [!] with the blocker."
)


def followup_for(event: dict) -> dict:
    if event.get("hook_event_name") != "stop" or event.get("status") in ("aborted", "error"):
        return {}
    ledger = run_folder.ledger_for(event)
    found = run_folder.check_ledger(ledger) if ledger else []
    if not found:
        return {}
    listed = "\n".join(f"- {problem}" for problem in found)
    return {"followup_message": f"Supercook ledger check:\n{listed}\n{FOLLOWUP_RULE}"}


def main() -> None:
    try:
        event = json.loads(sys.stdin.read())
        result = followup_for(event) if isinstance(event, dict) else {}
    except Exception:
        result = {}
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
