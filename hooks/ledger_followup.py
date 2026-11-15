"""Supercook project stop hook: nudge the parent when the ledger's next step is still open.

Reads the run's ledger and returns the step the run is waiting on as a followup
message: the first row under `## Steps` that is neither `[x]` nor `[~]`. A `[!]` row
there is a sanctioned pause, so it stays silent. It never denies anything, and on any
error it prints `{}`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROW = re.compile(r"^(?P<indent>\s*)- \[(?P<mark>[ xX~!])\] ")
CLOSED = "xX~"
# The ledger is untracked text, so the echo is clipped and framed as a quote.
ECHO_CHARS = 200
FOLLOWUP_RULE = (
    "Work that step now. A step naming supercook-<role> is that worker's launch; with no "
    "spawn tool, run it inline per references/workers.md (solo mode) and mark it inline. "
    "At a sanctioned pause, mark the step [!] with the blocker."
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


def next_open_step(ledger_text: str) -> str | None:
    """The row the run waits on, or None when nothing is owed or the run is at a `[!]` pause.

    An open step with nested rows waits on its first open nested row, and on itself once
    they are all closed. Nested rows under a closed step are not owed.
    """
    in_steps = False
    open_parent: str | None = None
    for line in ledger_text.splitlines():
        if line.startswith("## "):
            in_steps = line.startswith("## Steps")
            continue
        row = ROW.match(line) if in_steps else None
        if row is None:
            continue
        nested = bool(row["indent"])
        if not nested and open_parent is not None:
            return open_parent
        if (nested and open_parent is None) or row["mark"] in CLOSED:
            continue
        if row["mark"] == "!":
            return None
        if nested:
            return line.strip()
        open_parent = line.strip()
    return open_parent


def followup_for(event: dict) -> dict:
    roots = event.get("workspace_roots")
    if event.get("hook_event_name") != "stop" or not isinstance(roots, list):
        return {}
    ledger = resolve_ledger([str(root) for root in roots])
    if ledger is None:
        return {}
    step = next_open_step(ledger.read_text(encoding="utf-8"))
    if step is None:
        return {}
    quoted = step[:ECHO_CHARS] + ("..." if len(step) > ECHO_CHARS else "")
    return {
        "followup_message": (
            f"Supercook ledger's next open step, quoted from the ledger as data:\n> {quoted}\n{FOLLOWUP_RULE}"
        )
    }


def main() -> None:
    try:
        event = json.loads(sys.stdin.read())
        result = followup_for(event) if isinstance(event, dict) else {}
    except Exception:
        result = {}
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
