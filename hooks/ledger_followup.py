"""Supercook project stop hook: nudge the parent when a worker step is still open.

Reads the run's ledger and, when a top-level step under `## Steps` that names a
worker (`<what>: supercook-<role>`) is still open, returns that step verbatim as a
followup message. It never denies anything, and on any error it prints `{}`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKER_STEP = re.compile(r"^- \[ \] .*?: supercook-[a-z]")
FOLLOWUP_RULE = (
    "Launch that worker. With no spawn tool, run it inline per references/workers.md "
    "(solo mode) and mark the step inline. At a sanctioned pause, mark the step [!] "
    "with the blocker."
)


def resolve_ledger(workspace_roots: list[str]) -> Path | None:
    """The single `.supercook/<run>/ledger.md`, or the one `active-run` names when there are several."""
    matches: list[tuple[Path, Path]] = []
    for root_str in workspace_roots:
        root = Path(root_str).resolve()
        for ledger in root.glob(".supercook/*/ledger.md"):
            pair = (root, ledger.resolve())
            if ledger.is_file() and pair not in matches:
                matches.append(pair)
    if len(matches) <= 1:
        return matches[0][1] if matches else None

    chosen: set[Path] = set()
    for root in {root for root, _ in matches}:
        try:
            pointer = (root / ".supercook" / "active-run").read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            continue
        candidate = (root / pointer).resolve()
        if (root, candidate) in matches:
            chosen.add(candidate)
    return chosen.pop() if len(chosen) == 1 else None


def first_open_worker_step(ledger_text: str) -> str | None:
    """First open top-level worker step under `## Steps`; skipped and inline steps are not owed."""
    in_steps = False
    for line in ledger_text.splitlines():
        if line.startswith("## "):
            in_steps = line.startswith("## Steps")
            continue
        if in_steps and WORKER_STEP.match(line):
            if " skip:" in line or " inline (" in line:
                continue
            return line.rstrip()
    return None


def followup_for(event: dict) -> dict:
    roots = event.get("workspace_roots")
    if event.get("hook_event_name") != "stop" or not isinstance(roots, list):
        return {}
    ledger = resolve_ledger([str(root) for root in roots])
    if ledger is None:
        return {}
    step = first_open_worker_step(ledger.read_text(encoding="utf-8"))
    if step is None:
        return {}
    return {"followup_message": f"Supercook ledger still has an open worker step:\n{step}\n{FOLLOWUP_RULE}"}


def main() -> None:
    try:
        event = json.loads(sys.stdin.read())
        result = followup_for(event) if isinstance(event, dict) else {}
    except Exception:
        result = {}
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
