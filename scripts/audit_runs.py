#!/usr/bin/env python3
"""Audit local /supercook runs from Cursor agent transcripts (stdlib only).

For each top-level chat that attached the supercook skill, report which SKILL.md
was loaded and that plugin's version, subagent launches by type, hook denials the
agent mentioned, and the parent's own edits to files outside the run folder.

Transcripts record tool calls and the agent's text, not tool results, so a hook
denial shows up only when the agent says so. The version is the one the chat
announced on its first line; without that line it is read from the plugin copy on
disk now, which for a local checkout can be newer than what the chat ran. Edits
made through Shell (`sed -i`, heredocs) are not counted. `--since` compares the
transcript file's modification date, not the date the chat started.

Usage: python3 scripts/audit_runs.py [--root DIR] [--since YYYY-MM-DD] [--json] [FILE ...]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

DEFAULT_ROOT = Path.home() / ".cursor" / "projects"
SKILL_PATH = re.compile(r"Skill Name: supercook\s*\nPath: (\S+/skills/supercook/SKILL\.md)")
SPAWN_TOOLS = {"Task", "Subagent", "CreateAgent"}
EDIT_TOOLS = {"Write", "StrReplace", "Edit", "MultiEdit", "EditNotebook", "Delete"}
EDIT_PATH_KEYS = ("path", "file_path", "target_file", "target_notebook")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)
ROLE_NAME = re.compile(r"^(supercook-[a-z]+(?:-[a-z]+)*)\b")
# The 0.5 fallback brief opens with this line; a mention later in a prompt names no launch.
FILE_POINTER = re.compile(r"^Read \S*agents/(supercook-[a-z]+(?:-[a-z]+)*)\.md")
POINTER_TYPES = {"generalPurpose", "untyped"}
VERSION_LINE = re.compile(r"^supercook (\S+) from \S+", re.MULTILINE)
SPAWN_NONE = re.compile(r"\|\s*spawn:?\s+none\b")
DENIAL = re.compile(
    r"\bhook\b[^.\n]{0,80}\b(?:den(?:y|ied|ies)|block(?:ed|s)?|reject(?:ed|s)?)\b"
    r"|\b(?:den(?:y|ied|ies)|blocked|rejected)\b[^.\n]{0,80}\bhook\b",
    re.IGNORECASE,
)
NEGATION = re.compile(r"\b(?:not|never|no)\b|n['’]t\b", re.IGNORECASE)


def iter_transcripts(root: Path) -> Iterable[Path]:
    """Top-level chat transcripts only; subagent transcripts live one folder deeper."""
    for path in sorted(root.glob("*/agent-transcripts/*/*.jsonl")):
        if path.stem == path.parent.name:
            yield path


def load_entries(path: Path) -> list[dict[str, Any]]:
    entries = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def content_items(entry: dict[str, Any]) -> list[dict[str, Any]]:
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    return [item for item in content or [] if isinstance(item, dict)]


def plugin_version(skill_path: str) -> str | None:
    manifest = Path(skill_path).expanduser().parents[2] / ".cursor-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) else None


def install_label(skill_path: str) -> str:
    if "/plugins/local/" in skill_path:
        return "local"
    if "/plugins/cache/" in skill_path:
        return f"cache@{Path(skill_path).parents[2].name[:7]}"
    return "other"


def _as_dict(value: Any) -> dict[str, Any]:
    """CallDynamicTool arguments arrive as a dict or as a JSON string."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def unwrap(tool_name: str, tool_input: Any) -> tuple[str, Any]:
    """A CallDynamicTool call stands for the tool it names, with that tool's arguments."""
    if tool_name == "CallDynamicTool" and isinstance(tool_input, dict):
        return str(tool_input.get("toolName")), _as_dict(tool_input.get("arguments"))
    return tool_name, tool_input


def launch_role(tool_input: dict[str, Any]) -> str | None:
    """The supercook role a launch runs, in any shape the docs have prescribed, else None.

    Typed (`subagent_type`), 0.4 `custom` plus `name`, 0.3.10 role leading the
    `description`, and the 0.5 generalPurpose brief that opens by pointing at the agent file.
    """
    kind = str(tool_input.get("subagent_type") or tool_input.get("name") or "untyped")
    for value in (kind, tool_input.get("name"), tool_input.get("description")):
        match = ROLE_NAME.match(str(value or ""))
        if match:
            return match.group(1)
    if kind in POINTER_TYPES:
        pointer = FILE_POINTER.match(str(tool_input.get("prompt") or "").lstrip())
        if pointer:
            return pointer.group(1)
    return None


def launch_label(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Name a spawn call by its subagent type, plus the supercook role when the type is not that role."""
    if tool_name not in SPAWN_TOOLS:
        return None
    kind = str(tool_input.get("subagent_type") or tool_input.get("name") or "untyped")
    role = launch_role(tool_input)
    return f"{kind}:{role}" if role and role != kind else kind


def edited_paths(tool_name: str, tool_input: dict[str, Any] | str) -> list[str]:
    if tool_name in EDIT_TOOLS and isinstance(tool_input, dict):
        return [tool_input[key] for key in EDIT_PATH_KEYS if isinstance(tool_input.get(key), str)][:1]
    if tool_name == "ApplyPatch":
        patch = tool_input if isinstance(tool_input, str) else "\n".join(map(str, tool_input.values()))
        return [path.strip() for path in PATCH_FILE.findall(patch)]
    return []


def is_run_file(path: str) -> bool:
    """Run artifacts and plan files the parent is expected to write itself."""
    return (
        "/.supercook/" in path
        or path.startswith(".supercook/")
        or "/.cursor/plans/" in path
        or path.endswith(".plan.md")
    )


def is_supercook_launch(label: str) -> bool:
    return label.startswith("supercook-") or ":supercook-" in label


def audit_chat(path: Path) -> dict[str, Any] | None:
    """Return one chat's audit row, or None when the chat never attached the supercook skill."""
    entries = load_entries(path)
    skill_paths: list[str] = []
    launches: Counter[str] = Counter()
    product_edits: set[str] = set()
    denials: list[str] = []
    first_said: str | None = None
    solo = False
    for entry in entries:
        for item in content_items(entry):
            if item.get("type") == "text":
                text = str(item.get("text", ""))
                if entry.get("role") == "user":
                    skill_paths.extend(p for p in SKILL_PATH.findall(text) if p not in skill_paths)
                    continue
                first_said = text if first_said is None else first_said
                solo = solo or bool(SPAWN_NONE.search(text))
                denials.extend(m.group(0) for m in DENIAL.finditer(text) if not NEGATION.search(m.group(0)))
            elif item.get("type") == "tool_use":
                name, tool_input = unwrap(str(item.get("name")), item.get("input"))
                tool_input = tool_input if isinstance(tool_input, (dict, str)) else {}
                solo = solo or bool(SPAWN_NONE.search(json.dumps(tool_input)))
                label = launch_label(name, tool_input) if isinstance(tool_input, dict) else None
                if label:
                    launches[label] += 1
                product_edits.update(p for p in edited_paths(name, tool_input) if not is_run_file(p))
    if not skill_paths:
        return None
    announced = VERSION_LINE.search(first_said or "")
    return {
        "chat": path.stem,
        "project": path.parents[2].name if len(path.parents) > 2 else "",
        "modified": date.fromtimestamp(path.stat().st_mtime).isoformat(),
        "skills": [
            {"path": p, "install": install_label(p), "version": plugin_version(p)} for p in skill_paths
        ],
        "announced_version": announced.group(1) if announced else None,
        "solo": solo,
        "launches": dict(sorted(launches.items())),
        "hook_denials": len(denials),
        "denial_example": denials[0] if denials else None,
        "product_edits": sorted(product_edits),
    }


def install_version(chat: dict[str, Any]) -> str:
    """The first loaded copy's install and the version the chat ran, as far as the transcript shows."""
    first = chat["skills"][0]
    return f"{first['install']} {chat['announced_version'] or first['version'] or 'unknown'}"


def summarize(chats: list[dict[str, Any]]) -> dict[str, Any]:
    """Solo runs (`spawn none` on the capability line) have nothing to launch, so the launch counts skip them."""
    installs = Counter(install_version(chat) for chat in chats)
    delegating = [c for c in chats if not c["solo"]]
    no_launch = [c for c in delegating if not any(is_supercook_launch(k) for k in c["launches"])]
    with_implementer = [c for c in chats if any(k.endswith("supercook-implementer") for k in c["launches"])]
    edits_alone = [c for c in delegating if c["product_edits"] and c not in with_implementer]
    return {
        "chats": len(chats),
        "installs": dict(installs.most_common()),
        "solo_runs": len(chats) - len(delegating),
        "no_supercook_launch": len(no_launch),
        "implementer_launched": len(with_implementer),
        "parent_edits_without_implementer": len(edits_alone),
        "hook_denials_mentioned": sum(1 for c in chats if c["hook_denials"]),
    }


def format_report(chats: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = []
    for chat in chats:
        launches = ", ".join(f"{k.removeprefix('supercook-')} {v}" for k, v in chat["launches"].items()) or "none"
        extra = f" (+{len(chat['skills']) - 1} more skill paths)" if len(chat["skills"]) > 1 else ""
        solo = " (solo: spawn none)" if chat["solo"] else ""
        lines.append(f"{chat['modified']} {chat['project']} {chat['chat'][:8]}")
        lines.append(f"  skill: {install_version(chat)}{extra}")
        lines.append(f"  launches: {launches}{solo}")
        lines.append(f"  parent edits outside the run folder: {len(chat['product_edits'])}")
        if chat["hook_denials"]:
            lines.append(f"  hook denials mentioned: {chat['hook_denials']} ({chat['denial_example']})")
    lines.append("")
    lines.append(f"chats: {summary['chats']}")
    lines.append("installs: " + ", ".join(f"{k} x{v}" for k, v in summary["installs"].items()))
    for key in ("solo_runs", "no_supercook_launch", "implementer_launched", "parent_edits_without_implementer",
                "hook_denials_mentioned"):
        lines.append(f"{key.replace('_', ' ')}: {summary[key]}")
    return "\n".join(lines)


def collect(paths: Iterable[Path], since: date | None = None) -> list[dict[str, Any]]:
    chats = []
    for path in paths:
        try:
            if since and date.fromtimestamp(path.stat().st_mtime) < since:
                continue
            row = audit_chat(path)
        except OSError as error:
            print(f"skipped {path}: {error.strerror or error}", file=sys.stderr)
            continue
        if row:
            chats.append(row)
    return sorted(chats, key=lambda chat: chat["modified"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="*", type=Path, help="transcript files; default: every chat under --root")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--since", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                        help="skip transcripts last modified before this date")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of the report")
    args = parser.parse_args(argv)
    chats = collect(args.files or iter_transcripts(args.root), args.since)
    summary = summarize(chats)
    if args.json:
        print(json.dumps({"summary": summary, "chats": chats}, indent=2))
    else:
        print(format_report(chats, summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
