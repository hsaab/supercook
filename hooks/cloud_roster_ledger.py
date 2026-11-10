"""Ledger reader shared by the supercook project hooks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PHASE_ORDER = ("assess", "recon", "plan", "test-first", "implement", "verify")
_PHASE_ROW = re.compile(r"^- \[([ x~])\] ([^:]+):(.*)$")
_STARTED_LINE = re.compile(
    r"started:.*\btier:\s*(\S+).*?\btrack:\s*(\S+)",
    re.IGNORECASE,
)
_MODE_IN_STARTED = re.compile(r"\bmode:\s*(\S+)", re.IGNORECASE)


@dataclass(frozen=True)
class LedgerHeader:
    tier: str
    track: str
    mode: str | None


def resolve_ledger(workspace_roots: list[str]) -> Path | None:
    """Pick the single ledger under .supercook/<run>/ledger.md, or active-run when ambiguous."""
    matches: list[tuple[Path, Path]] = []
    for root_str in workspace_roots:
        root = Path(root_str).resolve()
        for ledger in root.glob(".supercook/*/ledger.md"):
            if ledger.is_file():
                matches.append((root, ledger.resolve()))

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
                chosen.append(ledger)

    if len(chosen) == 1:
        return chosen[0]
    return None


def parse_header(ledger_text: str) -> LedgerHeader:
    tier = "standard"
    track = "bugfix"
    mode: str | None = None
    for line in ledger_text.splitlines():
        if line.startswith("started:"):
            tier_match = _STARTED_LINE.search(line)
            if tier_match:
                tier = tier_match.group(1).strip()
                track = tier_match.group(2).strip().rstrip("|")
            mode_match = _MODE_IN_STARTED.search(line)
            if mode_match:
                mode = mode_match.group(1).strip().rstrip("|")
            break
    return LedgerHeader(tier=tier, track=track, mode=mode)


def _phase_rows(ledger_text: str) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    in_phases = False
    for line in ledger_text.splitlines():
        if line.startswith("## Phases"):
            in_phases = True
            continue
        if in_phases and line.startswith("## "):
            break
        if not in_phases:
            continue
        if line.startswith("  "):
            continue
        match = _PHASE_ROW.match(line)
        if not match:
            continue
        label = match.group(2).strip()
        if label in _PHASE_ORDER:
            rows[label] = (match.group(1), match.group(3))
    return rows


def _row_open(check: str, detail: str) -> bool:
    if check in ("x", "~"):
        return False
    if "skip:" in detail:
        return False
    if "degraded: parent inline (spawn none)" in detail:
        return False
    return check == " "


def _workers_for_phase(phase: str, header: LedgerHeader) -> list[str]:
    if phase == "assess":
        return ["supercook-assessor"]
    if phase == "recon":
        if header.tier == "trivial":
            return []
        return ["supercook-explorer"]
    if phase == "plan":
        if header.tier == "trivial":
            return []
        if header.track == "implement-plan":
            return ["supercook-plan-optimizer"]
        if header.tier == "complex":
            return [
                "supercook-arena-runner",
                "supercook-arena-runner",
                "supercook-arena-runner",
                "supercook-plan-judge",
            ]
        return ["supercook-planner"]
    if phase == "test-first":
        if header.tier == "trivial":
            return []
        return ["supercook-test-designer"]
    if phase == "implement":
        if header.mode == "review":
            return ["supercook-review-implementer"]
        return ["supercook-implementer"]
    if phase == "verify":
        return ["supercook-verifier"]
    return []


def owed_workers(ledger_text: str) -> list[str]:
    header = parse_header(ledger_text)
    rows = _phase_rows(ledger_text)
    owed: list[str] = []
    for phase in _PHASE_ORDER:
        row = rows.get(phase)
        if row is None:
            continue
        check, detail = row
        if not _row_open(check, detail):
            continue
        owed.extend(_workers_for_phase(phase, header))
    return owed
