#!/usr/bin/env python3
"""Checks the supercook parent runs on a worker's output (stdlib only).

A boundary in a worker's prompt is a request; these checks are the control.
Run from anywhere in the repo: paths are repo-relative and the test command runs
from the repo root. Each check prints what it found and exits 0 when it passes,
1 when it fails, and 2 when it could not run (a bad argument or ref, a git error,
a missing file, a test command that would not start or timed out).

  scope   every path changed since a commit, committed or not, is inside the
          allow list, and no test file changed
  red     the new tests fail on their red-evidence lines with the test designer's
          stub applied, and only test paths are left changed afterwards
  lines   reviewable and raw changed lines against the slice budget
  recipe  hash a verification recipe, or check it against the recorded hash

GLOBs are git pathspec globs, as recorded in the ledger: `*` stays inside one
folder, `**/` matches zero or more folders, a folder matches everything under it,
and a pattern with no `*` or `?` is a literal path, so `app/[id]/page.tsx` works.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

# Run folders are ignored, or committed under `keep ledger`; the tracked roster
# .supercook/models.md stays in scope.
NOT_SCOPED = (":(exclude,glob).supercook/*/**",)
# The line-accounting excludes, in git's default pathspec syntax where `*` crosses folders.
UNREVIEWABLE = ("*.lock", "*lock.yaml", "*lock.json", "*.snap", "vendor", "*generated*")
OUTPUT_TAIL = 40
COULD_NOT_RUN = (126, 127)  # the shell found the command but could not execute it, or found nothing


class GuardError(Exception):
    """A check could not run; main() reports it with exit code 2."""


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, encoding="utf-8", errors="surrogateescape")
    if result.returncode != 0:
        raise GuardError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def pathspecs(patterns: list[str] | None, magic: str = "") -> list[str]:
    return [f":({magic}{'glob' if '*' in p or '?' in p else 'literal'}){p}" for p in patterns or []]


def changes_since(start: str, specs: list[str]) -> dict[str, str]:
    """Path -> status (A, M, D, T, or ? when untracked) for each path that now differs from start."""
    fields = git("diff", "--name-status", "-z", "--no-renames", start, "--", *specs).split("\0")
    changes = dict(zip(fields[1::2], fields[0::2]))
    for path in git("ls-files", "-z", "--others", "--exclude-standard", "--", *specs).split("\0"):
        if path:
            changes[path] = "?"
    return changes


def undo_test_change(path: str, status: str, start: str) -> str:
    try:
        if status == "?":
            Path(path).unlink()
        else:
            # Restores modified and deleted tests, and removes ones absent at start.
            git("restore", f"--source={start}", "--staged", "--worktree", "--", f":(literal){path}")
    except (GuardError, OSError) as error:
        return f"test changed, could not undo: {path}: {error}"
    return f"deleted added test {path}" if status in ("?", "A") else f"restored test {path}"


def cmd_scope(args: argparse.Namespace) -> int:
    start = args.since or git("merge-base", args.base, "HEAD").strip()
    problems = 0
    if args.since and args.tests:
        for path, status in sorted(changes_since(start, pathspecs(args.tests)).items()):
            print(undo_test_change(path, status, start) if args.fix else f"test changed: {path}", flush=True)
            problems += 1
    # Under --since, test paths are reported above. At delivery (--base) the branch
    # carries the slice's own committed tests, so test globs count as allowed there.
    allowed = pathspecs(args.allow + (args.tests or []), "exclude,")
    for path in sorted(changes_since(start, [*allowed, *NOT_SCOPED])):
        print(f"out of scope: {path}")
        problems += 1
    print("scope: ok" if not problems else f"scope: {problems} problem(s)")
    return 1 if problems else 0


def patch_paths(patch: str) -> set[str]:
    # -z numstat rows are "added\tdeleted\tpath"; a rename empties path and adds source and target fields.
    return {field.rsplit("\t", 1)[-1] for field in git("apply", "--numstat", "-z", patch).split("\0")} - {""}


def run_suite(command: str, timeout: int) -> tuple[str, int | None]:
    """The suite's combined output and exit code; the code is None when it timed out."""
    # --cmd comes from the parent's own recon record, never from the worker-writable
    # ledger; the shell lets it use pipes and env vars. Its own session lets a timeout
    # or SIGTERM kill the runner's children along with the shell.
    suite = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True
    )
    try:
        output, code = suite.communicate(timeout=timeout)[0], suite.returncode
    except subprocess.TimeoutExpired:
        os.killpg(suite.pid, signal.SIGKILL)
        output, code = suite.communicate()[0], None
    finally:
        if suite.returncode is None:
            os.killpg(suite.pid, signal.SIGKILL)
    return output.decode(errors="replace"), code


def suite_verdict(args: argparse.Namespace) -> tuple[int, str]:
    if args.stub and set(args.stub) & set(changes_since("HEAD", pathspecs(args.tests))):
        return 1, "red: a --stub path matches the test globs"
    output, code = run_suite(args.cmd, args.timeout)
    print("\n".join(output.splitlines()[-OUTPUT_TAIL:]))
    if code is None:
        return 2, f"red: timed out after {args.timeout}s"
    if code < 0 or code in COULD_NOT_RUN:
        return 2, f"red: the test command could not run (exit {code})"
    if code == 0:
        return 1, "red: the suite passed, so these tests are not red"
    missing = [text for text in args.expect if text not in output]
    if missing:
        return 1, "red: the suite failed, but its output lacks: " + "; ".join(missing)
    return 0, "red: confirmed; every --expect line is in the failing output"


def cmd_red(args: argparse.Namespace) -> int:
    signal.signal(signal.SIGTERM, lambda signum, _frame: sys.exit(128 + signum))
    if args.patch:
        stray = patch_paths(args.patch) - set(args.stub)
        if stray:
            print("red: the stub patch changes paths outside --stub: " + ", ".join(sorted(stray)))
            return 1
        try:
            git("apply", args.patch)
        except GuardError as error:
            print(f"red: stub patch does not apply: {error}")
            return 1
    try:
        code, verdict = suite_verdict(args)
    finally:
        reversed_ok = not args.patch or subprocess.run(["git", "apply", "-R", args.patch]).returncode == 0
    if not reversed_ok:
        print("red: the stub patch did not reverse; restore the tree before continuing")
        return 2
    print(verdict)
    leftover = sorted(changes_since("HEAD", [*pathspecs(args.tests, "exclude,"), *NOT_SCOPED]))
    if leftover:
        print("red: only test paths may stay changed, found: " + ", ".join(leftover))
    return max(code, 1 if leftover else 0)


def changed_lines(base: str, specs: list[str]) -> int:
    """Added plus deleted lines since base, as git diff --numstat counts them, plus untracked files."""
    rows = git("diff", "--numstat", "-z", "--no-renames", base, "--", *specs).split("\0")
    total = sum(int(count) for row in rows for count in row.split("\t")[:2] if count.isdigit())
    untracked = git("ls-files", "-z", "--others", "--exclude-standard", "--", *specs).split("\0")
    return total + sum(Path(path).read_bytes().count(b"\n") for path in untracked if os.path.isfile(path))


def cmd_lines(args: argparse.Namespace) -> int:
    base = git("merge-base", args.base, "HEAD").strip()
    raw = changed_lines(base, [])
    reviewable = changed_lines(base, [f":(exclude){p}" for p in (*UNREVIEWABLE, *(args.exclude or []))])
    print(f"reviewable: {reviewable} | raw: {raw} | budget: {args.budget}")
    if reviewable > args.budget:
        print("lines: over budget; split the slice or log a cohesion exception")
        return 1
    return 0


def sha256_hex(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value.lower()):
        raise argparse.ArgumentTypeError(f"not a sha256 hex digest: {value!r}")
    return value.lower()


def cmd_recipe(args: argparse.Namespace) -> int:
    if args.sha and not Path(args.file).is_file():
        print(f"recipe: {args.file} is missing")
        return 1
    digest = hashlib.sha256(Path(args.file).read_bytes()).hexdigest()
    print(f"sha256: {digest}")
    if args.sha and args.sha != digest:
        print(f"recipe: changed since it was recorded as {args.sha}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    scope = commands.add_parser("scope", help="changed paths stay inside the allow list")
    scope.add_argument("--allow", nargs="+", required=True, metavar="GLOB", help="paths the worker may change")
    scope.add_argument("--tests", nargs="+", metavar="GLOB", help="test paths the worker must not change")
    start = scope.add_mutually_exclusive_group(required=True)
    start.add_argument("--since", metavar="SHA", help="the commit before the worker launched")
    start.add_argument("--base", metavar="REF", help="at delivery: the branch since REF; tests count as allowed")
    scope.add_argument("--fix", action="store_true", help="put changed tests back as they were at --since")
    scope.set_defaults(handler=cmd_scope)

    red = commands.add_parser("red", help="the new tests fail with the stub applied")
    red.add_argument("--cmd", required=True, help="the test command from your recon record")
    red.add_argument("--expect", nargs="+", required=True, metavar="TEXT", help="what each red-evidence line prints")
    red.add_argument("--tests", nargs="+", required=True, metavar="GLOB", help="the only paths left changed")
    red.add_argument("--patch", type=os.path.abspath, help="the test designer's red-stub.patch")
    red.add_argument("--stub", nargs="+", metavar="PATH", help="the stub paths the patch may change")
    red.add_argument("--timeout", type=int, default=1800, help="seconds before the run counts as not run")
    red.set_defaults(handler=cmd_red)

    lines = commands.add_parser("lines", help="reviewable and raw lines against the budget")
    lines.add_argument("--base", required=True, help="the slice's base branch or ref")
    lines.add_argument("--budget", type=int, default=500, help="reviewable lines allowed")
    lines.add_argument("--exclude", nargs="+", metavar="PATHSPEC", help="more unreviewable paths (`*` crosses /)")
    lines.set_defaults(handler=cmd_lines)

    recipe = commands.add_parser("recipe", help="hash a recipe, or check it against the recorded hash")
    modes = recipe.add_subparsers(dest="mode", required=True)
    modes.add_parser("hash", help="print the sha256 to record").add_argument("file")
    check = modes.add_parser("check", help="fail when the recipe changed or is missing")
    check.add_argument("file")
    check.add_argument("sha", type=sha256_hex)
    recipe.set_defaults(handler=cmd_recipe, sha=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "scope" and args.fix and not (args.since and args.tests):
        parser.error("scope --fix needs --since and --tests")
    if args.command == "red" and bool(args.patch) != bool(args.stub):
        parser.error("red --patch and --stub go together")
    try:
        if args.command != "recipe":
            os.chdir(git("rev-parse", "--show-toplevel").strip())
        return args.handler(args)
    except (GuardError, OSError) as error:
        print(f"guard: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
