"""preToolUse hook: deny subagent launches whose model does not match the roster (fail open)."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from roster import ROSTER_KEYS, LedgerModel, load_roster, parse_ledger_models

_SHIPPED_ROSTER = (
    Path(__file__).resolve().parent.parent / "skills/supercook/models.md"
)
_TAG_PATTERN = re.compile(
    r"^(supercook-role|supercook-run):[ \t]*(.+?)[ \t]*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Decision:
    permission: str
    agent_message: str | None = None


def worker_name(tool_input: dict) -> str:
    """Supercook roster identity from subagent_type or name when prefixed supercook-."""
    subagent_type = tool_input.get("subagent_type")
    if isinstance(subagent_type, str) and subagent_type.startswith("supercook-"):
        return subagent_type
    name = tool_input.get("name")
    if isinstance(name, str) and name.startswith("supercook-"):
        return name
    return ""


def parse_tag(prompt: str, tag: str) -> str | None:
    for match in _TAG_PATTERN.finditer(prompt):
        if match.group(1) == tag:
            return match.group(2).strip()
    return None


def resolve_paths(
    workspace_roots: list[str] | None,
    run_tag: str | None,
) -> tuple[Path | None, Path | None]:
    roots = [Path(root).resolve() for root in (workspace_roots or [])]
    first_root = roots[0] if roots else None

    run_folder: Path | None = None
    if run_tag:
        run_path = Path(run_tag)
        if run_path.is_absolute():
            run_folder = run_path.resolve()
        elif first_root is not None:
            run_folder = (first_root / run_tag).resolve()
        else:
            run_folder = run_path.resolve()

    repo_root: Path | None = None
    if roots:
        if run_folder is not None:
            for root in roots:
                try:
                    run_folder.relative_to(root)
                except ValueError:
                    continue
                repo_root = root
                break
        if repo_root is None:
            repo_root = first_root

    repo_override: Path | None = None
    if repo_root is not None:
        repo_override = repo_root / ".supercook" / "models.md"

    return run_folder, repo_override


def decide(
    tool_input: dict,
    roster: dict[str, str],
    ledger_models: dict[str, LedgerModel],
) -> Decision:
    prompt = tool_input.get("prompt")
    if not isinstance(prompt, str):
        prompt = ""
    roster_worker = worker_name(tool_input)
    model = tool_input.get("model")
    if "model" in tool_input and model is not None and not isinstance(model, str):
        model = str(model)

    role_tag = parse_tag(prompt, "supercook-role")

    if role_tag is None:
        if roster_worker.startswith("supercook-"):
            return Decision(
                "deny",
                agent_message=(
                    "This supercook launch is missing required prompt tags. "
                    "Add line-anchored supercook-role: <roster-key> and "
                    "supercook-run: <run folder> to the prompt."
                ),
            )
        return Decision("allow")

    role = role_tag.strip()
    if role not in ROSTER_KEYS:
        listed = ", ".join(sorted(ROSTER_KEYS))
        return Decision(
            "deny",
            agent_message=(
                f"supercook-role '{role}' is not a roster key. "
                f"Valid roster keys: {listed}"
            ),
        )

    if roster_worker.startswith("supercook-") and parse_tag(prompt, "supercook-run") is None:
        return Decision(
            "deny",
            agent_message=(
                "This supercook launch is missing supercook-run. "
                "Tell the parent to add line-anchored supercook-run: "
                "<run folder> to the prompt."
            ),
        )

    expected = roster.get(role, "")

    if expected == "inherit":
        if model is None:
            return Decision("allow")
        return Decision(
            "deny",
            agent_message=(
                f"Role {role} is rostered as inherit; omit the model on this launch."
            ),
        )

    if model == expected:
        return Decision("allow")

    if model is None:
        entry = ledger_models.get(role)
        if (
            entry is not None
            and entry.slug == "inherit"
            and entry.rejected_slug
        ):
            return Decision("allow")
        fallback_hint = ""
        if expected:
            fallback_hint = (
                f" If {expected} is unavailable, announce once at intake and record "
                f"'{role} inherit (unavailable {expected})' on the ledger models: header."
            )
        return Decision(
            "deny",
            agent_message=(
                f"Role {role} requires model {expected}; no model was passed."
                f"{fallback_hint}"
            ),
        )

    return Decision(
        "deny",
        agent_message=(
            f"Role {role} requires model {expected}, not {model}."
        ),
    )


def _emit(decision: Decision) -> None:
    payload: dict[str, str] = {"permission": decision.permission}
    if decision.agent_message:
        payload["agent_message"] = decision.agent_message
    print(json.dumps(payload), flush=True)


def main() -> None:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise TypeError("event payload must be an object")

        tool_input = event.get("tool_input")
        if not isinstance(tool_input, dict):
            tool_input = {}
            for key in ("subagent_type", "name", "model"):
                value = event.get(key)
                if value is not None:
                    tool_input[key] = value
            task = event.get("task")
            if task is not None:
                tool_input["prompt"] = task

        workspace_roots = event.get("workspace_roots")
        if workspace_roots is not None and not isinstance(workspace_roots, list):
            raise TypeError("workspace_roots must be a list")

        prompt = tool_input.get("prompt")
        if not isinstance(prompt, str):
            prompt = ""
        run_tag = parse_tag(prompt, "supercook-run")

        run_folder, repo_override = resolve_paths(workspace_roots, run_tag)
        home_models = Path.home() / ".supercook" / "models.md"
        roster = load_roster(repo_override, home_models, _SHIPPED_ROSTER)

        ledger_models: dict[str, LedgerModel] = {}
        if run_folder is not None:
            ledger_path = run_folder / "ledger.md"
            if ledger_path.is_file():
                ledger_models = parse_ledger_models(
                    ledger_path.read_text(encoding="utf-8")
                )

        decision = decide(tool_input, roster, ledger_models)
        _emit(decision)
        sys.exit(0)
    except Exception:
        _emit(Decision("allow"))
        sys.exit(0)


if __name__ == "__main__":
    main()
