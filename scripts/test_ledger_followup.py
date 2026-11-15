"""Smoke tests for scripts/ledger_followup.py, the stop hook, run the way Cursor runs it.

The checks themselves are tested in process in test_run_folder.py.
Run: python3 -m unittest discover -s scripts
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ledger_followup

HOOK = Path(ledger_followup.__file__).resolve()
LEDGER = (
    "# Ledger\ntier: standard | track: feature | big-change: no\nspawn: typed\n\n## Steps\n"
    "- [x] map the code: supercook-explorer (Task)\n- [ ] plan.md: supercook-planner\n"
)


class StopHookSmoke(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        run = self.root / ".supercook" / "run"
        run.mkdir(parents=True)
        (run / "ledger.md").write_text(LEDGER, encoding="utf-8")
        (self.root / ".supercook" / "active-run").write_text(".supercook/run/ledger.md\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, stdin_text=None, **event):
        if stdin_text is None:
            stdin_text = json.dumps({"hook_event_name": "stop", "workspace_roots": [str(self.root)], **event})
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=stdin_text, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_a_live_run_gets_every_problem_and_the_rule_in_one_followup(self):
        message = self.run_hook(status="completed")["followup_message"]
        self.assertIn("checked with no logged launch or agent id: step 1", message)
        self.assertIn("still open: step 2: plan.md: supercook-planner", message)
        self.assertIn(ledger_followup.FOLLOWUP_RULE, message)

    def test_a_finished_run_stays_silent_in_later_chats(self):
        (self.root / ".supercook" / "active-run").unlink()
        self.assertEqual(self.run_hook(), {})

    def test_an_aborted_or_failed_turn_is_not_nudged(self):
        for status in ("aborted", "error"):
            with self.subTest(status=status):
                self.assertEqual(self.run_hook(status=status), {})

    def test_bad_input_and_other_events_print_an_empty_object(self):
        samples = (
            "not json at all",
            "[]",
            json.dumps({"hook_event_name": "stop", "workspace_roots": 1}),
            json.dumps({"hook_event_name": "postToolUse", "workspace_roots": [str(self.root)]}),
        )
        for stdin_text in samples:
            with self.subTest(stdin=stdin_text):
                self.assertEqual(self.run_hook(stdin_text), {})


if __name__ == "__main__":
    unittest.main()
