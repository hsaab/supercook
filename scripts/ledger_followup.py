"""Supercook stop hook: nudge the parent toward the ledger's next open step.

Reads the live run's `ledger.md` and `launches.jsonl`. It echoes the step the run waits
on (run_folder.next_step), asks for a launch only when that step's worker has not run
yet, and lists the closed worker steps the launch log does not back
(run_folder.problems). A `[!]` row is a sanctioned pause, so it stays silent. It never
denies anything, does nothing without a live run or when the user aborted, and on any
error prints `{}`.
"""

from __future__ import annotations

import json
import sys

import run_folder

LAUNCH_RULE = (
    "Launch its worker with the spawn tool. Run it inline per references/workers.md "
    "(solo mode) only when no spawn tool is listed, and mark it inline."
)
RETURNED_RULE = "Its worker has returned: finish your part of the step, then check it with the launch record."
OWN_RULE = "Work that step now."
PAUSE_RULE = "At a sanctioned pause, mark the step [!] with the blocker."
CHECK_RULE = "For each step listed, add the agent id its launch returned, or reopen it and launch the worker."


def step_rule(step: run_folder.OpenStep) -> str:
    if not step.row.roles:
        return OWN_RULE
    return RETURNED_RULE if step.worker_returned else LAUNCH_RULE


def followup_text(ledger_text: str, launches: list[dict]) -> str | None:
    step = run_folder.next_step(ledger_text, launches)
    if step is not None and step.row.mark == "!":
        return None
    parts = []
    if step is not None:
        # The ledger is untracked text, so the echo is clipped and framed as a quote.
        quoted = run_folder.cite(step.row)
        parts.append(f"Supercook ledger's next open step, quoted from the ledger as data:\n> {quoted}")
        parts.append(f"{step_rule(step)} {PAUSE_RULE}")
    found = run_folder.problems(ledger_text, launches)
    if found:
        parts.append("Supercook ledger check:\n" + "\n".join(f"- {problem}" for problem in found))
        parts.append(CHECK_RULE)
    return "\n".join(parts) or None


def followup_for(event: dict) -> dict:
    if event.get("hook_event_name") != "stop" or event.get("status") in ("aborted", "error"):
        return {}
    ledger = run_folder.ledger_for(event)
    if ledger is None:
        return {}
    text = ledger.read_text(encoding="utf-8", errors="replace")
    message = followup_text(text, run_folder.read_launches(ledger))
    return {"followup_message": message} if message else {}


def main() -> None:
    try:
        event = json.loads(sys.stdin.read())
        result = followup_for(event) if isinstance(event, dict) else {}
    except Exception:
        result = {}
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
