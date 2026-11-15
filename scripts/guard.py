#!/usr/bin/env python3
"""Checks the supercook parent runs on a worker's output (stdlib only).

A boundary in a worker's prompt is a request; these checks are the control.
Run from inside the repo. Each subcommand prints what it found and exits 0 when
the check passes and 1 when it fails.

  scope   changed paths stay inside an allow list and test files stay untouched
  red     the suite fails with the temporary stub applied, then the stub reverses
  lines   reviewable and raw changed lines against the slice budget
  recipe  a verification recipe still has the sha256 recorded when it was written

Globs use fnmatch, so `*` also matches across folders; a pattern ending in `/` is
a folder prefix, and a leading `**/` also matches files at the repo root.

Usage:
  guard.py scope --allow GLOB... [--tests GLOB...] [--since SHA] [--base REF] [--fix]
  guard.py red --cmd "TEST COMMAND" [--patch FILE] [--timeout SECONDS]
  guard.py lines --base REF [--budget N] [--exclude GLOB...]
  guard.py recipe FILE [--sha HEX]
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import subprocess
import sys
from pathlib import Path

RUN_FOLDER = ".supercook/"
GENERATED = ("*.lock", "*lock.yaml", "*lock.json", "*.snap", "vendor/*", "*/vendor/*", "*generated*")
OUTPUT_TAIL = 40


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def matches(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        elif fnmatch.fnmatchcase(path, pattern):
            return True
        elif pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:]):
            return True
    return False


def working_changes() -> list[tuple[str, str]]:
    """(status, path) for every changed or untracked path, rename targets included."""
    fields = git("status", "--porcelain=v1", "-z", "--untracked-files=all").split("\0")
    changes = []
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if "R" in status or "C" in status:
            # -z puts the source in the next field; treat the move as an add plus a delete.
            source = fields[index]
            index += 1
            changes.append(("A ", path))
            if "R" in status:
                changes.append((" D", source))
            continue
        changes.append((status, path))
    return [(status, path) for status, path in changes if not path.startswith(RUN_FOLDER)]


def committed_paths(revision_range: str) -> list[str]:
    return [path for path in git("diff", "--name-only", revision_range).splitlines() if path]


def undo_test_change(status: str, path: str) -> str:
    if status == "??" or "A" in status:
        git("rm", "--cached", "--quiet", "--ignore-unmatch", "--", path)
        Path(path).unlink(missing_ok=True)
        return f"deleted added test {path}"
    git("restore", "--source=HEAD", "--staged", "--worktree", "--", path)
    return f"restored test {path}"


def cmd_scope(args: argparse.Namespace) -> int:
    problems: list[str] = []
    for status, path in working_changes():
        if args.tests and matches(path, args.tests):
            if args.fix:
                problems.append(undo_test_change(status, path))
            else:
                problems.append(f"test changed: {path}")
        elif not matches(path, args.allow):
            problems.append(f"out of scope: {path}")
    if args.since and args.tests:
        for path in committed_paths(f"{args.since}..HEAD"):
            if matches(path, args.tests):
                problems.append(f"test committed after {args.since}: {path}")
    if args.base:
        merge_base = git("merge-base", args.base, "HEAD").strip()
        for path in committed_paths(f"{merge_base}..HEAD"):
            allowed = args.allow + (args.tests or [])
            if not path.startswith(RUN_FOLDER) and not matches(path, allowed):
                problems.append(f"out of scope since {args.base}: {path}")
    for problem in problems:
        print(problem)
    print("scope: ok" if not problems else f"scope: {len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_red(args: argparse.Namespace) -> int:
    if args.patch:
        applied = subprocess.run(["git", "apply", args.patch], capture_output=True, text=True)
        if applied.returncode != 0:
            print(f"red: stub patch does not apply: {applied.stderr.strip()}")
            return 1
    try:
        # The test command comes from the run's own ledger and may use pipes or env vars.
        suite = subprocess.run(
            args.cmd, shell=True, capture_output=True, text=True, timeout=args.timeout
        )
        output, failed = suite.stdout + suite.stderr, suite.returncode != 0
    except subprocess.TimeoutExpired:
        output, failed = f"timed out after {args.timeout}s", False
    finally:
        reversed_ok = True
        if args.patch:
            reversed_ok = subprocess.run(["git", "apply", "-R", args.patch]).returncode == 0
    print("\n".join(output.splitlines()[-OUTPUT_TAIL:]))
    if not reversed_ok:
        print("red: the stub patch did not reverse; restore the tree before continuing")
        return 1
    if not failed:
        print("red: the suite did not fail, so these tests are not red")
        return 1
    print("red: confirmed; compare the failures above with red-evidence")
    return 0


def cmd_lines(args: argparse.Namespace) -> int:
    merge_base = git("merge-base", args.base, "HEAD").strip()
    excluded = list(GENERATED) + (args.exclude or [])
    raw = reviewable = 0
    for row in git("diff", "--numstat", merge_base).splitlines():
        added, deleted, path = row.split("\t", 2)
        count = (int(added) if added.isdigit() else 0) + (int(deleted) if deleted.isdigit() else 0)
        raw += count
        if not matches(path, excluded):
            reviewable += count
    print(f"reviewable: {reviewable} | raw: {raw} | budget: {args.budget}")
    if reviewable > args.budget:
        print("lines: over budget; split the slice or log a cohesion exception")
        return 1
    return 0


def cmd_recipe(args: argparse.Namespace) -> int:
    digest = hashlib.sha256(Path(args.file).read_bytes()).hexdigest()
    print(f"sha256: {digest}")
    if args.sha and args.sha.lower() != digest:
        print(f"recipe: changed since it was recorded as {args.sha}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Supercook parent checks.")
    commands = parser.add_subparsers(dest="command", required=True)

    scope = commands.add_parser("scope", help="changed paths stay inside the allow list")
    scope.add_argument("--allow", nargs="+", required=True, help="globs the worker may change")
    scope.add_argument("--tests", nargs="+", help="test globs the worker must not touch")
    scope.add_argument("--since", help="test commit sha; committed test edits after it fail")
    scope.add_argument("--base", help="also check every path committed since this ref")
    scope.add_argument("--fix", action="store_true", help="restore modified tests, delete added ones")
    scope.set_defaults(handler=cmd_scope)

    red = commands.add_parser("red", help="the suite fails with the stub applied")
    red.add_argument("--cmd", required=True, help="the recorded test command")
    red.add_argument("--patch", help="the test designer's red-stub.patch")
    red.add_argument("--timeout", type=int, default=1800)
    red.set_defaults(handler=cmd_red)

    lines = commands.add_parser("lines", help="reviewable and raw lines against the budget")
    lines.add_argument("--base", required=True, help="the slice's base branch or ref")
    lines.add_argument("--budget", type=int, default=500)
    lines.add_argument("--exclude", nargs="+", help="extra globs that do not count as reviewable")
    lines.set_defaults(handler=cmd_lines)

    recipe = commands.add_parser("recipe", help="a recipe file still matches its recorded hash")
    recipe.add_argument("file")
    recipe.add_argument("--sha", help="the sha256 recorded when the recipe was written")
    recipe.set_defaults(handler=cmd_recipe)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
