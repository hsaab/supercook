"""The supercook run folder, read by the hooks and by guard.py (stdlib only).

`.supercook/<run>/` holds `ledger.md` (written by the parent) and `launches.jsonl`
(written by launch_log.py, one row per launch that returned). The checks here compare
the two. They only ever produce messages; nothing in this module blocks.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Iterable, NamedTuple

LAUNCH_LOG = "launches.jsonl"
LAUNCH_TOOLS = {"Task", "Subagent", "CreateAgent"}
ROW = re.compile(r"^(?P<indent>\s*)- \[(?P<mark>[ xX~!])\] (?P<text>.*)$")
WORKERS = re.compile(r": (supercook-[a-z].*)$")
ROLE = re.compile(r"supercook-[a-z]+(?:-[a-z]+)*")
ROLE_NAME = re.compile(r"^(supercook-[a-z]+(?:-[a-z]+)*)\b")
# A fallback brief opens by pointing at the agent file ("Read" up to 0.6, "Follow" since);
# a mention later in a prompt names no launch.
FILE_POINTER = re.compile(r"^(?:Read|Follow) \S*agents/(supercook-[a-z]+(?:-[a-z]+)*)\.md")
POINTER_TYPES = {"generalPurpose", "untyped"}
AGENT_ID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
HEADER = re.compile(r"(?:^|\| )(tier|track|big-change|spawn): ([^\s|]+)", re.MULTILINE)
SKIP = re.compile(r"\bskip:(.*)$")
NEVER_SKIPPED = {"supercook-implementer", "supercook-verifier"}
SCOPE_MODIFIERS = {"plan only", "no pr", "no commits"}
ECHO_CHARS = 160


class Row(NamedTuple):
    number: str
    mark: str
    text: str
    roles: list[str]
    nested: bool


class OpenStep(NamedTuple):
    row: Row
    worker_returned: bool


def as_dict(value: object) -> dict | None:
    """Tool arguments arrive as a dict or as a JSON string."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def unwrap(tool_name: str, tool_input: object) -> tuple[str, object]:
    """A CallDynamicTool call stands for the tool it names, with that tool's arguments."""
    arguments = as_dict(tool_input)
    if tool_name == "CallDynamicTool" and arguments is not None:
        return str(arguments.get("toolName")), as_dict(arguments.get("arguments"))
    return tool_name, tool_input


def launch_call(tool_name: object, tool_input: object) -> dict | None:
    """A spawn call's arguments, also when routed through CallDynamicTool; None for any other tool."""
    tool_name, arguments = unwrap(str(tool_name), tool_input)
    arguments = as_dict(arguments)
    return arguments if tool_name in LAUNCH_TOOLS else None


def launch_role(call: dict) -> str | None:
    """The supercook role a launch runs, in any shape the docs have prescribed, else None.

    Typed (`subagent_type`), 0.4 `custom` plus `name`, 0.3.10 role leading the
    `description`, and the generalPurpose brief that opens by pointing at the agent file.
    """
    kind = str(call.get("subagent_type") or call.get("name") or "untyped")
    for value in (kind, call.get("name"), call.get("description")):
        match = ROLE_NAME.match(str(value or ""))
        if match:
            return match.group(1)
    if kind in POINTER_TYPES:
        pointer = FILE_POINTER.match(str(call.get("prompt") or "").lstrip())
        if pointer:
            return pointer.group(1)
    return None


def is_tracked(root: Path, path: Path) -> bool:
    try:
        listed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", str(path.relative_to(root))],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(listed.stdout.strip())


def run_ledger(roots: Iterable[Path]) -> Path | None:
    """The ledger of the one live run under these roots, or None.

    A run is live while `.supercook/active-run` names its ledger; the run deletes that
    pointer when it ends, so a finished run's folder stays silent. A pointer git tracks
    came with a clone, not from a run, so it never counts.
    """
    found: set[Path] = set()
    for root in {Path(root).resolve() for root in roots}:
        base = root / ".supercook"
        pointer = base / "active-run"
        try:
            if pointer.is_symlink():
                continue
            ledger = (root / pointer.read_text(encoding="utf-8").strip()).resolve()
        except (OSError, UnicodeDecodeError):
            continue
        # resolve() follows links, so a symlinked run folder or .supercook lands outside base.
        if ledger.name == "ledger.md" and ledger.parent.parent == base and ledger.is_file():
            if not is_tracked(root, pointer):
                found.add(ledger)
    return found.pop() if len(found) == 1 else None


def ledger_for(event: dict) -> Path | None:
    """The live run ledger for a hook event's workspace roots and working directory."""
    roots = event.get("workspace_roots")
    if not isinstance(roots, list):
        return None
    return run_ledger(Path(str(root)) for root in [*roots, event.get("cwd")] if root)


def read_launches(ledger: Path) -> list[dict]:
    """Logged launches beside the ledger, one per tool_use_id, since a plugin and a project hook can both log a call."""
    try:
        text = (ledger.parent / LAUNCH_LOG).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rows, seen = [], set()
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or not row.get("role"):
            continue
        key = row.get("tool_use_id")
        if key is None or key not in seen:
            seen.add(key)
            rows.append(row)
    return rows


def steps(ledger_text: str) -> list[Row]:
    """Every row under `## Steps`, numbered like `3` or `2.4`.

    Only a worker step, written `<what>: supercook-<role>` as the playbooks write it, has
    roles. A row that only mentions a worker, or sits under one, launches nothing.
    """
    rows: list[Row] = []
    in_steps = False
    top = child = 0
    for line in ledger_text.splitlines():
        if line.startswith("## "):
            in_steps = line.startswith("## Steps")
            continue
        match = ROW.match(line) if in_steps else None
        if match is None:
            continue
        nested = bool(match["indent"])
        top, child = (top, child + 1) if nested else (top + 1, 0)
        workers = WORKERS.search(match["text"])
        roles = ROLE.findall(workers.group(1)) if workers else []
        number = f"{top}.{child}" if nested else str(top)
        rows.append(Row(number, match["mark"].lower(), match["text"].strip(), roles, nested))
    return rows


def cite(row: Row) -> str:
    return f"step {row.number}: {row.text[:ECHO_CHARS]}{'...' if len(row.text) > ECHO_CHARS else ''}"


def valid_skip(reason: str, header: dict[str, str], row: Row) -> bool:
    """A skip cites the run's own tier, track, `big-change: no`, or a scope modifier.

    Implement and verify take only `plan only`, since every other reason still ships code.
    A nested row may also cite `no findings`: review and merge fixes run only on findings.
    """
    words = reason.lower().replace(":", " ").split()
    lead = " ".join(words[:2])
    if row.nested and lead == "no findings":
        return True
    if NEVER_SKIPPED & set(row.roles):
        return lead == "plan only"
    if words[:1] in (["tier"], ["track"]):
        return len(words) > 1 and words[1] == header.get(words[0])
    if words[:1] == ["big-change"]:
        return words[1:2] == ["no"] and header.get("big-change") == "no"
    return lead in SCOPE_MODIFIERS


def match_launches(rows: list[Row], launches: list[dict]) -> tuple[set[str], list[str]]:
    """Give each checked worker step its own evidence: an agent id on the row, or one logged
    launch of a role it names that no other row has used.

    Returns the numbers of checked steps left without any, and the roles of unused launches.
    """
    recorded = {agent_id for row in rows for agent_id in AGENT_ID.findall(row.text)}
    unused = [
        str(launch["role"]) for launch in launches
        if not recorded & set(AGENT_ID.findall(str(launch.get("agent_id"))))
    ]
    bare: set[str] = set()
    for row in rows:
        if row.mark != "x" or not row.roles or " inline (" in row.text or AGENT_ID.search(row.text):
            continue
        role = next((role for role in unused if role in row.roles), None)
        if role is None:
            bare.add(row.number)
        else:
            unused.remove(role)
    return bare, unused


def problems(ledger_text: str, launches: list[dict]) -> list[str]:
    """One message per closed worker step the record does not back, citing it by number.

    Open steps are never a problem here: a slice PR is delivered with later slices open.
    """
    header = dict(HEADER.findall(ledger_text.split("## Steps", 1)[0]))
    rows = steps(ledger_text)
    bare, _ = match_launches(rows, launches)
    found: list[str] = []
    for row in rows:
        if not row.roles:
            continue
        skip = SKIP.search(row.text)
        if row.mark == "~" and skip is None:
            found.append(f"marked skipped with no skip: reason: {cite(row)}")
        elif row.mark == "~" and not valid_skip(skip.group(1), header, row):
            rule = (
                "implement and verify are never skipped unless plan only, launch the worker"
                if NEVER_SKIPPED & set(row.roles)
                else "a skip must cite this run's tier, track, big-change: no, or a scope modifier"
            )
            found.append(f"{rule}: {cite(row)}")
        elif row.mark == "x" and " inline (" in row.text and header.get("spawn") != "none":
            found.append(f"inline is only for spawn: none, launch the worker: {cite(row)}")
        elif row.number in bare:
            found.append(f"checked with no logged launch or agent id: {cite(row)}")
    return found


def next_step(ledger_text: str, launches: list[dict]) -> OpenStep | None:
    """The step the run waits on: the first row neither `[x]` nor `[~]`, else None.

    An open step with nested rows waits on its first open nested row, and on itself once
    they are all closed; nested rows under a closed step are not owed. A `[!]` row is
    returned as is, since the caller must treat it as a pause. A `[ ]` row is open even
    with `skip:` on it. `worker_returned` is set when the step is a worker step whose launch
    is already recorded, so what is left is the parent's own part of it.
    """
    rows = steps(ledger_text)
    waiting: Row | None = None
    open_parent: Row | None = None
    for row in rows:
        if not row.nested and open_parent is not None:
            waiting = open_parent
            break
        if (row.nested and open_parent is None) or row.mark in "x~":
            continue
        if row.mark == "!" or row.nested:
            waiting = row
            break
        open_parent = row
    waiting = waiting or open_parent
    if waiting is None:
        return None
    _, unused = match_launches(rows, launches)
    returned = bool(waiting.roles) and (
        bool(AGENT_ID.search(waiting.text)) or any(role in waiting.roles for role in unused)
    )
    return OpenStep(waiting, returned)


def check_ledger(ledger: Path) -> list[str]:
    """problems() for a ledger file and the launch log beside it."""
    return problems(ledger.read_text(encoding="utf-8", errors="replace"), read_launches(ledger))
