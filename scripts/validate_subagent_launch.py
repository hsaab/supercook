"""Validate and build CallDynamicTool Task envelopes and CreateAgent launch payloads (stdlib only)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TASK_NAMESPACE = "cursor"
TASK_TOOL_NAME = "Task"
ENVELOPE_KEYS = frozenset({"namespace", "toolName", "arguments"})

REQUIRED_FIELDS = ("description", "subagent_type", "prompt")
OPTIONAL_STRING_FIELDS = ("model", "environment", "cloud_base_branch", "resume")
BOOLEAN_FIELDS = ("run_in_background", "interrupt")
STRING_LIST_FIELDS = ("file_attachments",)
LAUNCH_FIELDS = frozenset(REQUIRED_FIELDS + OPTIONAL_STRING_FIELDS + BOOLEAN_FIELDS + STRING_LIST_FIELDS)

ENVIRONMENTS = ("local", "cloud")

BUILDER_FLAGS = frozenset({
    "description", "subagent_type", "prompt_file", "model",
    "environment", "cloud_base_branch", "run_in_background",
})


@dataclass(frozen=True)
class TaskLaunchSpec:
    description: str
    subagent_type: str
    prompt: str
    model: str | None = None
    environment: str | None = None
    cloud_base_branch: str | None = None
    run_in_background: bool = False

    def to_arguments(self) -> dict[str, object]:
        out: dict[str, object] = {
            "description": self.description,
            "subagent_type": self.subagent_type,
            "prompt": self.prompt,
        }
        if self.model is not None:
            out["model"] = self.model
        if self.environment is not None:
            out["environment"] = self.environment
        if self.cloud_base_branch is not None:
            out["cloud_base_branch"] = self.cloud_base_branch
        if self.run_in_background:
            out["run_in_background"] = True
        return out


def parse_stdin(text: str) -> tuple[object | None, list[str]]:
    if not text.strip():
        return None, ["stdin: expected a JSON object"]
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [f"stdin: invalid JSON ({exc.msg})"]
    if not isinstance(value, dict):
        return None, ["stdin: expected a JSON object"]
    return value, []


def _path(prefix: str, field: str) -> str:
    return f"{prefix}{field}" if prefix else field


def validate_launch_fields(fields: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        path = _path(prefix, field)
        if field not in fields:
            errors.append(f"{path}: missing required field")
            continue
        value = fields[field]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}: must be a non-empty string")

    for field in OPTIONAL_STRING_FIELDS:
        if field not in fields:
            continue
        path = _path(prefix, field)
        value = fields[field]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}: must be a non-empty string")
            continue
        if field == "environment" and value not in ENVIRONMENTS:
            errors.append(f'{path}: must be "local" or "cloud"')

    for field in BOOLEAN_FIELDS:
        if field not in fields:
            continue
        if not isinstance(fields[field], bool):
            errors.append(f"{_path(prefix, field)}: must be a boolean")

    if "file_attachments" in fields:
        path = _path(prefix, "file_attachments")
        value = fields["file_attachments"]
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"{path}: must be a list of non-empty strings")

    if "cloud_base_branch" in fields and fields.get("environment") != "cloud":
        branch_path = _path(prefix, "cloud_base_branch")
        errors.append(f'{branch_path}: only valid when {_path(prefix, "environment")} is "cloud"')

    if "model" in fields and "resume" in fields:
        model_path = _path(prefix, "model")
        errors.append(f"{model_path}: must not be set together with {_path(prefix, 'resume')}")

    for key in sorted(fields.keys() - LAUNCH_FIELDS):
        errors.append(f"{_path(prefix, key)}: unknown field")

    return errors


def validate_task_envelope(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key in ("namespace", "toolName"):
        if key not in envelope:
            errors.append(f"{key}: missing required field")
            continue
        expected = TASK_NAMESPACE if key == "namespace" else TASK_TOOL_NAME
        if envelope[key] != expected:
            errors.append(f'{key}: must be "{expected}"')

    arguments: dict[str, Any] = {}
    if "arguments" not in envelope or not isinstance(envelope["arguments"], dict):
        errors.append("arguments: missing required object")
    else:
        arguments = envelope["arguments"]

    errors.extend(validate_launch_fields(arguments, "arguments."))

    for field in sorted(LAUNCH_FIELDS & envelope.keys()):
        errors.append(f"{field}: Task field at top level; move it under arguments")

    for key in sorted(envelope.keys() - ENVELOPE_KEYS - LAUNCH_FIELDS):
        errors.append(f"{key}: unknown field")

    return errors


def validate_task_payload(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["stdin: expected a JSON object"]
    if payload.keys() & ENVELOPE_KEYS:
        return validate_task_envelope(payload)
    return validate_launch_fields(payload, "arguments.")


def validate_create_agent(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["stdin: expected a JSON object"]
    errors: list[str] = []
    nested = payload.get("arguments")
    if isinstance(nested, dict):
        for field in sorted(LAUNCH_FIELDS & nested.keys()):
            msg = "CreateAgent field nested under arguments; move it to the top level"
            errors.append(f"arguments.{field}: {msg}")
    errors.extend(validate_launch_fields(payload, ""))
    return errors


def read_prompt_file(path_text: str) -> tuple[str | None, list[str]]:
    path = Path(path_text)
    if not path.is_file():
        return None, [f"--prompt-file: file not found: {path_text}"]
    try:
        raw = path.read_bytes()
    except OSError as err:
        return None, [f"--prompt-file: cannot read: {path_text} ({err})"]
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, ["--prompt-file: not valid UTF-8"]
    if not text.strip():
        return None, ["--prompt-file: file is empty"]
    return text, []


def build_task_envelope(spec: TaskLaunchSpec) -> dict[str, object]:
    envelope: dict[str, object] = {
        "namespace": TASK_NAMESPACE,
        "toolName": TASK_TOOL_NAME,
        "arguments": spec.to_arguments(),
    }
    errors = validate_task_envelope(envelope)
    if errors:
        raise ValueError("\n".join(errors))
    return envelope


def _emit_errors(errors: list[str]) -> int:
    for line in errors:
        print(line, file=sys.stderr)
    return 1


def _run_validate(validate_fn, stdin_text: str) -> int:
    payload, parse_errors = parse_stdin(stdin_text)
    if parse_errors:
        return _emit_errors(parse_errors)
    assert payload is not None
    errors = validate_fn(payload)
    if errors:
        return _emit_errors(errors)
    print("ok")
    return 0


def _non_empty_str(value: object | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _builder_flag_is_set(ns: argparse.Namespace, name: str) -> bool:
    if name == "run_in_background":
        return bool(ns.run_in_background)
    return _non_empty_str(getattr(ns, name, None))


def _required_builder_fields_present(ns: argparse.Namespace) -> bool:
    return all(_non_empty_str(getattr(ns, name)) for name in ("description", "subagent_type", "prompt_file"))


def _task_build_ns(ns: argparse.Namespace) -> int:
    prompt, file_errors = read_prompt_file(ns.prompt_file)
    if file_errors:
        return _emit_errors(file_errors)
    assert prompt is not None
    spec = TaskLaunchSpec(
        description=ns.description,
        subagent_type=ns.subagent_type,
        prompt=prompt,
        model=ns.model,
        environment=ns.environment,
        cloud_base_branch=ns.cloud_base_branch,
        run_in_background=bool(ns.run_in_background),
    )
    try:
        envelope = build_task_envelope(spec)
    except ValueError as exc:
        return _emit_errors(str(exc).splitlines())
    print(json.dumps(envelope))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or build supercook subagent launches.")
    sub = parser.add_subparsers(dest="command", required=True)
    task = sub.add_parser("task", help="Validate Task on stdin or build from flags.")
    task.add_argument("--description")
    task.add_argument("--subagent-type")
    task.add_argument("--prompt-file")
    task.add_argument("--model")
    task.add_argument("--environment", choices=ENVIRONMENTS)
    task.add_argument("--cloud-base-branch")
    task.add_argument("--run-in-background", action="store_true")

    sub.add_parser("create-agent", help="Validate CreateAgent payload on stdin.")
    ns = parser.parse_args(argv)
    if ns.command == "create-agent":
        return _run_validate(validate_create_agent, sys.stdin.read())
    if _required_builder_fields_present(ns):
        return _task_build_ns(ns)
    if any(_builder_flag_is_set(ns, name) for name in BUILDER_FLAGS):
        missing = [
            flag for flag, attr in (
                ("--description", "description"),
                ("--subagent-type", "subagent_type"),
                ("--prompt-file", "prompt_file"),
            ) if not _non_empty_str(getattr(ns, attr))
        ]
        parser.error(" ".join(f"{f} is required when building a launch" for f in missing))

    return _run_validate(validate_task_payload, sys.stdin.read())


if __name__ == "__main__":
    sys.exit(main())
