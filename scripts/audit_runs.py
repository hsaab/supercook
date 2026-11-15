#!/usr/bin/env python3
"""Audit local /supercook runs from Cursor agent transcripts (stdlib only).

For each top-level chat that attached the supercook skill, report which SKILL.md
was loaded and that plugin's version, subagent launches by type, hook denials the
agent mentioned, and the parent's own edits to files outside the run folder.

Transcripts record tool calls and the agent's text, not tool results, so a hook
denial shows up only when the agent says so. The version is read from the plugin
copy on disk now, which for a local checkout can be newer than what the chat ran.

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
AGENT_FILE = re.compile(r"agents/(supercook-[a-z]+(?:-[a-z]+)*)\.md")
DENIAL = re.compile(
    r"\bhook\b[^.\n]{0,80}\b(?:den(?:y|ied|ies)|block(?:ed|s)?|reject(?:ed|s)?)\b"
    r"|\b(?:den(?:y|ied|ies)|blocked|rejected)\b[^.\n]{0,80}\bhook\b",
    re.IGNORECASE,
)


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
    manifest = Path(skill_path).parents[2] / ".cursor-plugin" / "plugin.json"
    try:
        version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None
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


def launch_label(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Name a spawn call by its subagent type; a fallback launch also names the agent file it points at."""
    if tool_name == "CallDynamicTool":
        if tool_input.get("toolName") not in SPAWN_TOOLS:
            return None
        tool_input = _as_dict(tool_input.get("arguments"))
    elif tool_name not in SPAWN_TOOLS:
        return None
    kind = tool_input.get("subagent_type") or tool_input.get("name") or "untyped"
    if not str(kind).startswith("supercook-"):
        pointer = AGENT_FILE.search(f"{tool_input.get('description', '')} {tool_input.get('prompt', '')}")
        if pointer:
            return f"{kind}:{pointer.group(1)}"
    return str(kind)


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
    for entry in entries:
        for item in content_items(entry):
            if item.get("type") == "text":
                text = str(item.get("text", ""))
                if entry.get("role") == "user":
                    skill_paths.extend(p for p in SKILL_PATH.findall(text) if p not in skill_paths)
                else:
                    denials.extend(match.group(0) for match in DENIAL.finditer(text))
            elif item.get("type") == "tool_use":
                name, tool_input = str(item.get("name")), item.get("input")
                tool_input = tool_input if isinstance(tool_input, (dict, str)) else {}
                label = launch_label(name, tool_input) if isinstance(tool_input, dict) else None
                if label:
                    launches[label] += 1
                product_edits.update(p for p in edited_paths(name, tool_input) if not is_run_file(p))
    if not skill_paths:
        return None
    return {
        "chat": path.stem,
        "project": path.parents[2].name,
        "modified": date.fromtimestamp(path.stat().st_mtime).isoformat(),
        "skills": [
            {"path": p, "install": install_label(p), "version": plugin_version(p)} for p in skill_paths
        ],
        "launches": dict(sorted(launches.items())),
        "hook_denials": len(denials),
        "denial_example": denials[0] if denials else None,
        "product_edits": sorted(product_edits),
    }


def summarize(chats: list[dict[str, Any]]) -> dict[str, Any]:
    installs: Counter[str] = Counter()
    for chat in chats:
        first = chat["skills"][0]
        installs[f"{first['install']} {first['version'] or 'unknown'}"] += 1
    no_launch = [c for c in chats if not any(is_supercook_launch(k) for k in c["launches"])]
    with_implementer = [c for c in chats if any(k.endswith("supercook-implementer") for k in c["launches"])]
    edits_alone = [c for c in chats if c["product_edits"] and c not in with_implementer]
    return {
        "chats": len(chats),
        "installs": dict(installs.most_common()),
        "no_supercook_launch": len(no_launch),
        "implementer_launched": len(with_implementer),
        "parent_edits_without_implementer": len(edits_alone),
        "hook_denials_mentioned": sum(1 for c in chats if c["hook_denials"]),
    }


def format_report(chats: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = []
    for chat in chats:
        first = chat["skills"][0]
        launches = ", ".join(f"{k.removeprefix('supercook-')} {v}" for k, v in chat["launches"].items()) or "none"
        extra = f" (+{len(chat['skills']) - 1} more skill paths)" if len(chat["skills"]) > 1 else ""
        lines.append(f"{chat['modified']} {chat['project']} {chat['chat'][:8]}")
        lines.append(f"  skill: {first['install']} {first['version'] or 'unknown'}{extra}")
        lines.append(f"  launches: {launches}")
        lines.append(f"  parent edits outside the run folder: {len(chat['product_edits'])}")
        if chat["hook_denials"]:
            lines.append(f"  hook denials mentioned: {chat['hook_denials']} ({chat['denial_example']})")
    lines.append("")
    lines.append(f"chats: {summary['chats']}")
    lines.append("installs: " + ", ".join(f"{k} x{v}" for k, v in summary["installs"].items()))
    for key in ("no_supercook_launch", "implementer_launched", "parent_edits_without_implementer",
                "hook_denials_mentioned"):
        lines.append(f"{key.replace('_', ' ')}: {summary[key]}")
    return "\n".join(lines)


def collect(paths: Iterable[Path], since: date | None = None) -> list[dict[str, Any]]:
    chats = []
    for path in paths:
        if since and date.fromtimestamp(path.stat().st_mtime) < since:
            continue
        row = audit_chat(path)
        if row:
            chats.append(row)
    return sorted(chats, key=lambda chat: chat["modified"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="*", type=Path, help="transcript files; default: every chat under --root")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--since", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date())
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
