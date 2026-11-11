"""Ledger reader for the supercook stop hook."""

from __future__ import annotations

import re
from pathlib import Path

_ROSTER_PHASES = ("assess", "recon", "plan", "test-first", "implement", "verify")
_OPEN_ROW = re.compile(r"^- \[ \] (" + "|".join(_ROSTER_PHASES) + r"):")


def resolve_ledger(workspace_roots: list[str]) -> Path | None:
    """Pick the single ledger under .supercook/<run>/ledger.md, or active-run when ambiguous."""
    matches: list[tuple[Path, Path]] = []
    for root_str in workspace_roots:
        root = Path(root_str).resolve()
        for ledger in root.glob(".supercook/*/ledger.md"):
            if ledger.is_file():
                pair = (root, ledger.resolve())
                if pair not in matches:
                    matches.append(pair)

    if not matches:
        return None
    if len(matches) == 1:
        return matches[0][1]

    chosen: list[Path] = []
    roots_seen = {root for root, _ in matches}
    for root in roots_seen:
        active_path = root / ".supercook" / "active-run"
        if not active_path.is_file():
            continue
        try:
            rel = active_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            continue
        candidate = (root / rel).resolve()
        for match_root, ledger in matches:
            if match_root == root and ledger == candidate:
                if ledger not in chosen:
                    chosen.append(ledger)

    if len(chosen) == 1:
        return chosen[0]
    return None


def first_open_row(ledger_text: str) -> str | None:
    """Return the first unchecked roster phase row under ## Phases, verbatim.

    Only top-level rows count. Indented rows, checked rows, skipped rows (`[~]`),
    blocked rows (`[!]`), and malformed open rows that say ` skip:` or ` inline (`
    on the same line are not owed. Intake names the worker on every roster row, so
    echoing the row tells the parent which worker is next.
    """
    in_phases = False
    for line in ledger_text.splitlines():
        if line.startswith("## Phases"):
            in_phases = True
            continue
        if in_phases and line.startswith("## "):
            break
        if in_phases and _OPEN_ROW.match(line):
            if " skip:" in line or " inline (" in line:
                continue
            return line.rstrip()
    return None
