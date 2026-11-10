"""Product-edit gate decisions from hook event facts (no ledger imports)."""

from __future__ import annotations

from pathlib import Path

EDIT_TOOLS = frozenset({"Write", "StrReplace", "ApplyPatch", "Delete", "EditNotebook"})
_PATH_KEYS = ("path", "file_path", "target_file")
_PARENT_ONLY_PHASES = frozenset({"test-first", "implement"})
_BLOCK_ALL_PHASES = frozenset({"assess", "recon", "plan"})


def is_parent_call(event: dict) -> bool:
    """Parent tool calls omit parent_agent_id and carry a non-empty transcript path."""
    parent_agent_id = event.get("parent_agent_id")
    if isinstance(parent_agent_id, str) and parent_agent_id != "":
        return False
    transcript = event.get("transcript_path")
    return isinstance(transcript, str) and transcript != ""


def _resolve_path(raw: str, roots: list[str]) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    if roots:
        return (Path(roots[0]) / path).resolve()
    return path.resolve()


def _under_supercook(edit_path: str, roots: list[str]) -> bool:
    resolved = _resolve_path(edit_path, roots)
    for root_str in roots:
        root = Path(root_str).resolve()
        supercook = root / ".supercook"
        try:
            resolved.relative_to(supercook)
            return True
        except ValueError:
            continue
    return False


def _outside_all_roots(edit_path: str, roots: list[str]) -> bool:
    if not roots:
        return True
    resolved = _resolve_path(edit_path, roots)
    for root_str in roots:
        root = Path(root_str).resolve()
        try:
            resolved.relative_to(root)
            return False
        except ValueError:
            continue
    return True


def _deny_message(owed_worker: str, owed_phase: str) -> str:
    return (
        f"Product edits are blocked while {owed_phase} is still open. "
        f"Launch {owed_worker} instead of writing product source. "
        "Pick the spawn fields from the tool schema. "
        "If supercook-<role> is a listed type, use that listed type. "
        "If the type field accepts a free value and the tool has a name field, "
        "set the type to custom and the name to supercook-<role>. "
        "Otherwise use the general-purpose type, put supercook-<role> in the "
        "description, and pass the agent file as the prompt."
    )


def _deny_payload(owed_worker: str, owed_phase: str) -> dict:
    message = _deny_message(owed_worker, owed_phase)
    return {
        "permission": "deny",
        "agent_message": message,
        "user_message": message,
    }


def decide_edit(
    event: dict,
    roots: list[str],
    owed_phase: str | None,
    owed_worker: str | None,
) -> dict:
    """Allow or deny a preToolUse edit from resolved ledger phase and caller shape."""
    tool_name = event.get("tool_name")
    if tool_name not in EDIT_TOOLS:
        return {"permission": "allow"}

    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return {"permission": "allow"}

    edit_path: str | None = None
    for key in _PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            edit_path = value
            break
    if edit_path is None:
        return {"permission": "allow"}

    if _under_supercook(edit_path, roots) or _outside_all_roots(edit_path, roots):
        return {"permission": "allow"}

    if owed_phase is None or owed_worker is None:
        return {"permission": "allow"}

    if owed_phase in _BLOCK_ALL_PHASES:
        return _deny_payload(owed_worker, owed_phase)

    if owed_phase in _PARENT_ONLY_PHASES:
        if is_parent_call(event):
            return _deny_payload(owed_worker, owed_phase)
        return {"permission": "allow"}

    return {"permission": "allow"}
