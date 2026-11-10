"""stop hook: nudge the parent when supercook phase workers are still open (fail open)."""

from __future__ import annotations

import json
import sys

from cloud_roster_ledger import owed_workers, resolve_ledger


def followup_text(workers: list[str]) -> str:
    names = ", ".join(workers)
    lines = [
        f"Supercook still owes these workers, in phase order: {names}.",
        "Launch the next one now instead of doing its phase yourself.",
        "Pick the spawn fields from the tool schema.",
        "If supercook-<role> is a listed type, launch that listed type.",
        (
            "If the type field accepts a free value and the tool has a name field, "
            "set the type to custom and the name to supercook-<role>."
        ),
        (
            "Otherwise use the general-purpose type, put supercook-<role> in the "
            "description, and pass the agent file as the prompt."
        ),
        (
            "When plan-optimizer is not a listed type, plan-optimizer takes that "
            "last branch on today's older install."
        ),
        (
            "A thin or wrong return gets a fresh relaunch with a corrected brief and "
            "the roster model, and you do not rebuild the result yourself."
        ),
        "An in-flight launch is recorded on the ledger and is not duplicated.",
    ]
    return "\n".join(lines)


def main() -> None:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise TypeError("event must be an object")
        if event.get("hook_event_name") != "stop":
            print("{}", flush=True)
            sys.exit(0)
        workspace_roots = event.get("workspace_roots")
        if not isinstance(workspace_roots, list):
            raise TypeError("workspace_roots must be a list")
        roots = [str(item) for item in workspace_roots]
    except Exception:
        print("{}", flush=True)
        sys.exit(0)

    ledger_path = resolve_ledger(roots)
    if ledger_path is None:
        print("{}", flush=True)
        sys.exit(0)

    try:
        ledger_text = ledger_path.read_text(encoding="utf-8")
    except OSError:
        print("{}", flush=True)
        sys.exit(0)

    workers = owed_workers(ledger_text)
    if not workers:
        print("{}", flush=True)
        sys.exit(0)

    message = followup_text(workers)
    print(json.dumps({"followup_message": message}), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
