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

    def write_ledger(self, *rows):
        (self.root / ".supercook" / "run" / "ledger.md").write_text(
            LEDGER.split("## Steps\n")[0] + "## Steps\n" + "\n".join(rows) + "\n", encoding="utf-8"
        )

    def test_the_next_step_is_quoted_with_a_launch_nudge_and_every_problem_listed(self):
        message = self.run_hook(status="completed")["followup_message"]
        self.assertIn("quoted from the ledger as data:\n> step 2: plan.md: supercook-planner\n", message)
        self.assertIn(ledger_followup.LAUNCH_RULE, message)
        self.assertIn("checked with no logged launch or agent id: step 1", message)
        self.assertIn(ledger_followup.CHECK_RULE, message)

    def test_a_step_whose_worker_returned_is_not_sent_back_for_a_relaunch(self):
        self.write_ledger("- [ ] find the root cause: supercook-explorer (you name the cause)")
        (self.root / ".supercook" / "run" / "launches.jsonl").write_text('{"role": "supercook-explorer"}\n', "utf-8")
        message = self.run_hook()["followup_message"]
        self.assertIn(ledger_followup.RETURNED_RULE, message)
        self.assertNotIn(ledger_followup.LAUNCH_RULE, message)

    def test_the_parents_own_step_is_echoed_before_a_later_worker(self):
        self.write_ledger("- [ ] reproduce it (yours)", "- [ ] plan.md: supercook-planner")
        message = self.run_hook()["followup_message"]
        self.assertIn("> step 1: reproduce it (yours)", message)
        self.assertIn(ledger_followup.OWN_RULE, message)

    def test_a_sanctioned_pause_stays_silent(self):
        self.write_ledger("- [x] map the code: supercook-explorer", "- [!] design doc (awaiting approval)",
                          "- [ ] plan.md: supercook-planner")
        self.assertEqual(self.run_hook(), {})

    def test_a_closed_and_backed_ledger_stays_silent(self):
        self.write_ledger("- [x] map the code: supercook-explorer (Task 7c1e4b52-9d0a-4f3e-8a21-5b6d0c9e1f34)")
        self.assertEqual(self.run_hook(), {})

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
