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
    leaf: bool


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


def worker_rows(ledger_text: str) -> list[Row]:
    """Every row under `## Steps` that names a worker, numbered like `3` or `2.4`.

    A nested row names its own worker or inherits its parent step's. A worker step with
    nested rows is judged by those rows (one launch per slice), so it is not a leaf.
    """
    rows: list[Row] = []
    in_steps = False
    top = child = 0
    parent_roles: list[str] = []
    parent_index: int | None = None
    for line in ledger_text.splitlines():
        if line.startswith("## "):
            in_steps = line.startswith("## Steps")
            continue
        match = ROW.match(line) if in_steps else None
        if match is None:
            continue
        workers = WORKERS.search(match["text"])
        own = ROLE.findall(workers.group(1)) if workers else []
        nested = bool(match["indent"])
        if nested:
            child += 1
            number, roles = f"{top}.{child}", own or parent_roles
            if roles and parent_index is not None:
                rows[parent_index] = rows[parent_index]._replace(leaf=False)
        else:
            top, child = top + 1, 0
            number, roles, parent_roles, parent_index = str(top), own, own, len(rows) if own else None
        if roles:
            rows.append(Row(number, match["mark"].lower(), match["text"].strip(), roles, nested, True))
    return rows


def valid_skip(reason: str, header: dict[str, str], nested: bool) -> bool:
    """A skip cites the run's own tier, track, `big-change: no`, or a scope modifier.

    A nested review row may also cite `no findings`, since it only runs when there are some.
    """
    words = reason.lower().replace(":", " ").split()
    if words[:1] in (["tier"], ["track"]):
        return len(words) > 1 and words[1] == header.get(words[0])
    if words[:1] == ["big-change"]:
        return words[1:2] == ["no"] and header.get("big-change") == "no"
    return " ".join(words[:2]) in SCOPE_MODIFIERS or (nested and words[:2] == ["no", "findings"])


def problems(ledger_text: str, launches: list[dict]) -> list[str]:
    """One message per problem, citing the step by number with its text clipped.

    Each checked leaf row needs its own evidence: an agent id on the row, or one logged
    launch of a role it names that no other row has used.
    """
    header = dict(HEADER.findall(ledger_text.split("## Steps", 1)[0]))
    rows = worker_rows(ledger_text)
    recorded = {agent_id for row in rows for agent_id in AGENT_ID.findall(row.text)}
    unused = [
        str(launch["role"]) for launch in launches
        if not recorded & set(AGENT_ID.findall(str(launch.get("agent_id"))))
    ]
    found: list[str] = []
    first_open = None
    for row in rows:
        cite = f"step {row.number}: {row.text[:ECHO_CHARS]}{'...' if len(row.text) > ECHO_CHARS else ''}"
        skip = SKIP.search(row.text)
        if skip and not row.nested and NEVER_SKIPPED & set(row.roles):
            found.append(f"implement and verify are never skipped, launch the worker: {cite}")
        elif skip and not valid_skip(skip.group(1), header, row.nested):
            found.append(f"a skip must cite this run's tier, track, big-change: no, or a scope modifier: {cite}")
        elif skip:
            continue
        elif row.mark == "~":
            found.append(f"marked skipped with no skip: reason: {cite}")
        elif " inline (" in row.text:
            if header.get("spawn") != "none":
                found.append(f"inline is only for spawn: none, launch the worker: {cite}")
        elif row.mark == "x" and row.leaf and not AGENT_ID.search(row.text):
            role = next((role for role in unused if role in row.roles), None)
            if role is None:
                found.append(f"checked with no logged launch or agent id: {cite}")
            else:
                unused.remove(role)
        elif row.mark == " " and first_open is None:
            first_open = cite
    if first_open:
        found.append(f"still open: {first_open}")
    return found


def check_ledger(ledger: Path) -> list[str]:
    """problems() for a ledger file and the launch log beside it."""
    return problems(ledger.read_text(encoding="utf-8", errors="replace"), read_launches(ledger))
