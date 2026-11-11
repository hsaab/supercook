"""Stop-hook journeys for hooks/cloud_roster_guard.py.

A parent ends a turn. The hook reads the ledger and, when a roster row is still
open, echoes the first one verbatim. Run: python3 -m unittest hooks.test_cloud_roster_guard
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# discover -s hooks puts this directory on sys.path. Importing as hooks.test_* does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cloud_roster_guard

GUARD = Path(cloud_roster_guard.__file__).resolve()

PHASE_ROWS = {
    "assess": "supercook-assessor via Task, grok-4.7-high",
    "recon": "supercook-explorer via Task, composer-2.5",
    "plan": "supercook-planner via Task",
    "test-first": "supercook-test-designer via Task",
    "implement": "supercook-implementer, one launch per slice",
    "verify": "supercook-verifier, fresh launch",
}


def ledger(open_labels=(), replacements=None, trailing=()):
    """Header lines from a real run ledger, then ## Phases and top-level rows."""
    replacements = replacements or {}
    lines = [
        "# Ledger: stop hook fixture",
        "run-id: fixture-run",
        "started: 2026-11-09 21:30 | tier: standard | track: bugfix",
        "capabilities: git yes | spawn Task | parent-host cloud-agent",
        "models: standard grok-4.7-high | implementer composer-2.5",
        "",
        "## Phases",
    ]
    for label, worker in PHASE_ROWS.items():
        if label in replacements:
            lines.append(replacements[label])
        else:
            state = " " if label in open_labels else "x"
            lines.append(f"- [{state}] {label}: {worker}")
    lines.extend(("- [ ] deliver", "- [~] merge. skip: no merge asked for", *trailing))
    return "\n".join(lines) + "\n"


def write_ledger(root, run_id, text, mtime=None):
    path = root / ".supercook" / run_id / "ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


class CloudRosterGuardTests(unittest.TestCase):
    def run_hook(self, root, stdin_text=None, copies=1):
        if stdin_text is None:
            stdin_text = json.dumps({"hook_event_name": "stop", "workspace_roots": [str(root)] * copies})
        done = subprocess.run(
            [sys.executable, str(GUARD)], input=stdin_text, capture_output=True,
            text=True, timeout=10, cwd=root,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            self.fail(f"stdout is not JSON: {done.stdout!r}")

    def followup(self, root, **kwargs):
        payload = self.run_hook(root, **kwargs)
        self.assertEqual(set(payload), {"followup_message"}, payload)
        return payload["followup_message"]

    def test_stop_echoes_the_first_open_row_verbatim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(("recon", "plan", "implement")))
            message = self.followup(root)
            self.assertIn("- [ ] recon: supercook-explorer via Task, composer-2.5", message)
            self.assertNotIn("supercook-planner", message)
            self.assertNotIn("supercook-implementer", message)

    def test_stop_message_covers_launch_inline_and_sanctioned_pause(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(("verify",)))
            message = self.followup(root)
            for phrase in ("Launch that worker", "run it inline", "mark the row inline", "[!]", "blocker"):
                self.assertIn(phrase, message)

    def test_stop_with_the_same_root_listed_twice_still_echoes_one_row(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(("recon",)))
            message = self.followup(root, copies=2)
            self.assertEqual(message.count("- [ ] recon:"), 1, message)

    def test_stop_ignores_rows_that_are_not_owed(self):
        # [~] skipped, [!] blocked, [x] done, indented rows, and rows outside the
        # roster (deliver, design doc, merge) never trigger a followup.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(
                replacements={
                    "recon": "- [~] recon: supercook-explorer. skip: assessor trivial",
                    "plan": "- [!] plan: supercook-planner blocked: waiting on design doc approval",
                },
                trailing=("  - [ ] recon: supercook-explorer", "  - [ ] implement: supercook-implementer"),
            ))
            self.assertEqual(self.run_hook(root), {})

    def test_stop_treats_a_checked_inline_row_as_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(replacements={
                "recon": "- [x] recon: supercook-explorer inline (spawn none)",
            }))
            self.assertEqual(self.run_hook(root), {})

    def test_stop_ignores_malformed_open_rows_with_skip_or_inline_markers(self):
        # A top-level `- [ ]` row that carries skip/inline text is not owed work.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(
                replacements={
                    "recon": "- [ ] recon: supercook-explorer. skip: assessor trivial",
                    "plan": "- [ ] plan: supercook-planner inline (spawn none)",
                },
            ))
            self.assertEqual(self.run_hook(root), {})

    def test_stop_with_no_ledger_is_silent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            text = ledger(("implement",))
            (root / ".supercook").mkdir()
            (root / ".supercook" / "ledger.md").write_text(text, encoding="utf-8")
            nested = root / ".supercook" / "run" / "nested"
            nested.mkdir(parents=True)
            (nested / "ledger.md").write_text(text, encoding="utf-8")
            self.assertEqual(self.run_hook(root), {})

    def test_stop_with_two_ledgers_and_no_pointer_is_silent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "older", ledger(("implement",)), 1_700_000_000)
            write_ledger(root, "newer", ledger(("recon",)), 1_800_000_000)
            self.assertEqual(self.run_hook(root), {})
            # A pointer that names neither ledger does not pick between them either.
            (root / ".supercook" / "active-run").write_text(".supercook/missing/ledger.md\n", encoding="utf-8")
            self.assertEqual(self.run_hook(root), {})

    def test_stop_with_undecodable_active_run_is_silent(self):
        # Two ledgers force the pointer to be read. Bytes that are not UTF-8 must fail open.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "older", ledger(("implement",)), 1_700_000_000)
            write_ledger(root, "newer", ledger(("recon",)), 1_800_000_000)
            (root / ".supercook" / "active-run").write_bytes(b"\xff\xfe\xfd")
            self.assertEqual(self.run_hook(root), {})

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores mode bits")
    def test_stop_with_unreadable_active_run_is_silent(self):
        # A mode 000 pointer is unreadable for a non-root user. Put the mode back so the temp dir can be removed.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "older", ledger(("implement",)), 1_700_000_000)
            write_ledger(root, "newer", ledger(("recon",)), 1_800_000_000)
            pointer = root / ".supercook" / "active-run"
            pointer.write_text(".supercook/newer/ledger.md\n", encoding="utf-8")
            mode = pointer.stat().st_mode & 0o777
            pointer.chmod(0o000)
            try:
                self.assertEqual(self.run_hook(root), {})
            finally:
                pointer.chmod(mode)

    def test_stop_uses_active_run_when_several_ledgers_exist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "older", ledger(("implement",)), 1_700_000_000)
            write_ledger(root, "newer", ledger(("recon", "plan", "implement")), 1_800_000_000)
            (root / ".supercook" / "active-run").write_text(".supercook/older/ledger.md\n", encoding="utf-8")
            message = self.followup(root)
            self.assertIn("- [ ] implement:", message)
            self.assertNotIn("recon", message)

    def test_stop_error_prints_an_empty_object(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(("recon",)))
            samples = ("not json at all", "[]", json.dumps({"hook_event_name": "stop", "workspace_roots": 1}))
            for stdin_text in samples:
                with self.subTest(stdin=stdin_text):
                    self.assertEqual(self.run_hook(root, stdin_text), {})

    def test_task_post_tool_use_prints_an_empty_object(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(("recon",)))
            event = {
                "hook_event_name": "postToolUse", "tool_name": "Task",
                "tool_input": {"subagent_type": "supercook-explorer", "prompt": "map"},
                "workspace_roots": [str(root)],
            }
            self.assertEqual(self.run_hook(root, json.dumps(event)), {})


if __name__ == "__main__":
    unittest.main()
