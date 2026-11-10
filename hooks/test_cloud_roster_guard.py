"""Stop-hook journeys for hooks/cloud_roster_guard.py.

A parent ends a turn. The hook reads the ledger and, when workers are still owed,
prints a followup that names them. Run: python3 -m unittest hooks.test_cloud_roster_guard
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# discover -s hooks puts this directory on sys.path. Importing as hooks.test_* does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cloud_roster_guard

GUARD = Path(cloud_roster_guard.__file__).resolve()

# Checked rows name who ran, and that name must not be copied out. Open rows say
# "not started" so the followup has to name the worker from the phase map.
CHECKED = {
    "assess": "supercook-assessor via Task (typed), grok-4.7-high (21:33)",
    "recon": "supercook-explorer via Task (typed), composer-2.5 (21:52)",
    "plan": "supercook-planner via Task (typed) (22:16)",
    "test-first": "supercook-test-designer via Task (typed) (22:24)",
    "implement": "supercook-implementer via Task (typed), composer-2.5 (22:31)",
    "verify": "supercook-verifier, fresh launch",
}
PHASES = ("assess", "recon", "plan", "test-first", "implement", "verify")
WORKERS = (
    "supercook-assessor", "supercook-explorer", "supercook-planner", "supercook-plan-optimizer",
    "supercook-arena-runner", "supercook-plan-judge", "supercook-test-designer",
    "supercook-implementer", "supercook-verifier", "supercook-review-implementer",
)
SCHEMA_PHRASES = (
    "listed type", "free value", "name field", "supercook-<role>", "general-purpose",
    "agent file as the prompt", "plan-optimizer takes that last branch on today's older install",
    "relaunch", "in-flight launch is recorded", "duplicated",
)


def others(*kept):
    return tuple(name for name in WORKERS if name not in kept)


def ledger(tier, track, open_labels, mode=None, replacements=None, trailing=()):
    """Header lines from a real run ledger, then ## Phases and top-level rows."""
    replacements = replacements or {}
    mode_part = f" | mode: {mode}" if mode else ""
    lines = [
        "# Ledger: stop hook fixture",
        "run-id: fixture-run",
        "repo: https://github.com/hsaab/supercook.git | branch: fixture | worktree: /tmp/fixture",
        f"started: 2026-11-09 21:30 | tier: {tier} | track: {track}{mode_part}",
        "capabilities: git yes | host github | tests `python3 -m unittest discover -s hooks`",
        "models: standard grok-4.7-high | explorer composer-2.5 | implementer composer-2.5 | plan-optimizer inherit",
        "ui-change: no | ui-source: none | render-check: none",
        "",
        "## Phases",
    ]
    for label in PHASES:
        if label in replacements:
            lines.append(replacements[label])
        else:
            state = " " if label in open_labels else "x"
            detail = "not started" if label in open_labels else CHECKED[label]
            lines.append(f"- [{state}] {label}: {detail}")
        if label == "recon":
            lines.append("- [~] design doc. skip: big-change no")
    lines.extend(("- [ ] deliver", "- [~] merge. skip: no merge asked for, run ends at the open PR", *trailing))
    return "\n".join(lines) + "\n"


def write_ledger(root, run_id, text, mtime=None):
    path = root / ".supercook" / run_id / "ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


class CloudRosterGuardTests(unittest.TestCase):
    def run_hook(self, root, stdin_text=None):
        if stdin_text is None:
            stdin_text = json.dumps({"hook_event_name": "stop", "workspace_roots": [str(root)]})
        done = subprocess.run(
            [sys.executable, str(GUARD)], input=stdin_text, capture_output=True,
            text=True, timeout=10, cwd=root,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            self.fail(f"stdout is not JSON: {done.stdout!r}")

    def followup(self, root):
        payload = self.run_hook(root)
        self.assertEqual(set(payload), {"followup_message"}, payload)
        message = payload["followup_message"]
        self.assertIsInstance(message, str)
        self.assertTrue(message.strip(), payload)
        return message

    def spoken(self, tier, track, open_labels, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(tier, track, open_labels, **kwargs))
            return self.followup(root)

    def assert_order(self, message, names):
        cursor = -1
        for name in names:
            found = message.find(name, cursor + 1)
            self.assertGreater(found, cursor, f"{name} missing or out of order in: {message}")
            cursor = found

    def assert_workers(self, message, names):
        self.assert_order(message, names)
        for name in others(*names):
            self.assertNotIn(name, message, message)

    def assert_schema_and_relaunch(self, message):
        for phrase in SCHEMA_PHRASES:
            self.assertIn(phrase, message)
        self.assertIsNone(re.search(r"\bresume\b", message, re.IGNORECASE), message)
        sentences = [part for part in re.split(r"[.!?\n]+", message) if re.search(r"\bcustom\b", part)]
        self.assertTrue(sentences, message)
        for sentence in sentences:
            self.assertIn("free value", sentence, sentence)
            self.assertIn("name field", sentence, sentence)

    def test_stop_with_open_recon_names_every_remaining_worker(self):
        owed = (
            "supercook-explorer", "supercook-planner", "supercook-test-designer",
            "supercook-implementer", "supercook-verifier",
        )
        message = self.spoken("standard", "bugfix", ("recon", "plan", "test-first", "implement", "verify"))
        self.assert_workers(message, owed)
        self.assert_schema_and_relaunch(message)

    def test_stop_on_trivial_demands_implement_and_verify_only(self):
        message = self.spoken("trivial", "bugfix", ("recon", "plan", "test-first", "implement", "verify"))
        self.assert_workers(message, ("supercook-implementer", "supercook-verifier"))

    def test_stop_on_implement_plan_demands_the_optimizer(self):
        message = self.spoken("standard", "implement-plan", ("plan", "test-first", "implement", "verify"))
        self.assert_workers(message, (
            "supercook-plan-optimizer", "supercook-test-designer",
            "supercook-implementer", "supercook-verifier",
        ))

    def test_stop_on_complex_plan_names_arena_then_judge(self):
        message = self.spoken("complex", "bugfix", ("plan",))
        self.assert_workers(message, ("supercook-arena-runner",) * 3 + ("supercook-plan-judge",))
        self.assertEqual(message.count("supercook-arena-runner"), 3, message)

    def test_stop_on_review_mode_demands_the_review_implementer(self):
        message = self.spoken("standard", "bugfix", ("implement",), mode="review")
        self.assert_workers(message, ("supercook-review-implementer",))

    def test_stop_when_only_deliver_is_open_is_silent(self):
        # [~] and a row whose text contains skip: are not owed. Indented checkbox
        # lines are not phase rows. deliver, design doc, and merge are not workers.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger(
                "standard", "bugfix", (),
                replacements={
                    "plan": "- [~] plan: supercook-planner",
                    "test-first": "- [ ] test-first: skip: supercook-test-designer",
                },
                trailing=("  - [ ] recon: supercook-explorer", "  - [ ] implement: supercook-implementer"),
            ))
            self.assertEqual(self.run_hook(root), {})

    def test_stop_with_no_ledger_is_silent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            text = ledger("standard", "bugfix", ("implement",))
            (root / ".supercook").mkdir()
            (root / ".supercook" / "ledger.md").write_text(text, encoding="utf-8")
            nested = root / ".supercook" / "run" / "nested"
            nested.mkdir(parents=True)
            (nested / "ledger.md").write_text(text, encoding="utf-8")
            self.assertEqual(self.run_hook(root), {})

    def test_stop_with_two_ledgers_and_no_pointer_is_silent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "older", ledger("standard", "bugfix", ("implement",)), 1_700_000_000)
            write_ledger(root, "newer", ledger("standard", "bugfix", ("recon",)), 1_800_000_000)
            self.assertEqual(self.run_hook(root), {})
            # A pointer that names neither ledger does not pick between them either.
            (root / ".supercook" / "active-run").write_text(".supercook/missing/ledger.md\n", encoding="utf-8")
            self.assertEqual(self.run_hook(root), {})

    def test_stop_with_undecodable_active_run_is_silent(self):
        # Two ledgers force the pointer to be read. Bytes that are not UTF-8 must fail open.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "older", ledger("standard", "bugfix", ("implement",)), 1_700_000_000)
            write_ledger(root, "newer", ledger("standard", "bugfix", ("recon",)), 1_800_000_000)
            (root / ".supercook" / "active-run").write_bytes(b"\xff\xfe\xfd")
            self.assertEqual(self.run_hook(root), {})

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores mode bits")
    def test_stop_with_unreadable_active_run_is_silent(self):
        # A mode 000 pointer is unreadable for a non-root user. Put the mode back so the temp dir can be removed.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "older", ledger("standard", "bugfix", ("implement",)), 1_700_000_000)
            write_ledger(root, "newer", ledger("standard", "bugfix", ("recon",)), 1_800_000_000)
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
            write_ledger(root, "older", ledger("standard", "bugfix", ("implement",)), 1_700_000_000)
            write_ledger(
                root, "newer",
                ledger("standard", "bugfix", ("recon", "plan", "test-first", "implement", "verify")),
                1_800_000_000,
            )
            (root / ".supercook" / "active-run").write_text(".supercook/older/ledger.md\n", encoding="utf-8")
            self.assert_workers(self.followup(root), ("supercook-implementer",))

    def test_stop_with_spawn_none_degraded_row_does_not_demand_it(self):
        message = self.spoken("standard", "bugfix", ("implement",), replacements={
            "recon": "- [ ] recon: supercook-explorer degraded: parent inline (spawn none)",
        })
        self.assert_workers(message, ("supercook-implementer",))

    def test_stop_error_prints_an_empty_object(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_ledger(root, "run", ledger("standard", "bugfix", ("recon",)))
            samples = ("not json at all", "[]", json.dumps({"hook_event_name": "stop", "workspace_roots": 1}))
            for stdin_text in samples:
                with self.subTest(stdin=stdin_text):
                    self.assertEqual(self.run_hook(root, stdin_text), {})


if __name__ == "__main__":
    unittest.main()
