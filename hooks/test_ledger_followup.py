"""Stop-hook journeys for hooks/ledger_followup.py.

A parent ends a turn. The hook reads the ledger and, when a worker step is still
open, echoes the first one verbatim. Run: python3 -m unittest discover -s hooks
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# discover -s hooks puts this directory on sys.path. Importing as hooks.test_* does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ledger_followup

HOOK = Path(ledger_followup.__file__).resolve()

STEPS = [
    "- [x] map the code the feature touches: supercook-explorer, a broad launch then one per area (Task, composer-2.5)",
    "- [~] design doc, big-change only (yours, with the user) skip: big-change no",
    "- [ ] plan.md names the data shape: supercook-planner, per references/plan.md",
    "- [ ] journey tests land red before the code: supercook-test-designer, per references/test-first.md",
    "- [ ] implement slice by slice: supercook-implementer, one launch per slice",
    "- [ ] open one PR per slice (yours), per references/deliver.md",
]


def ledger(steps=STEPS):
    header = [
        "# Ledger: stop hook fixture",
        "run-id: fixture-run | repo: git@example.com:acme/api.git | branch: supercook/fixture",
        "tier: standard | track: feature | big-change: no",
        "",
        "## Steps",
    ]
    log = ["", "## Log", "- 09:14 assess: tier: standard | track: feature"]
    return "\n".join([*header, *steps, *log]) + "\n"


def write_ledger(root, run_id, text):
    path = root / ".supercook" / run_id / "ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class StopFollowupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, stdin_text=None, copies=1):
        if stdin_text is None:
            stdin_text = json.dumps({"hook_event_name": "stop", "workspace_roots": [str(self.root)] * copies})
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=stdin_text, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def followup(self, **kwargs):
        payload = self.run_hook(**kwargs)
        self.assertEqual(set(payload), {"followup_message"}, payload)
        return payload["followup_message"]

    def test_echoes_the_first_open_worker_step_verbatim(self):
        write_ledger(self.root, "run", ledger())
        message = self.followup()
        self.assertIn(STEPS[2], message)
        self.assertIn(ledger_followup.FOLLOWUP_RULE, message)
        self.assertNotIn("supercook-test-designer", message)

    def test_the_same_root_listed_twice_still_echoes_one_step(self):
        write_ledger(self.root, "run", ledger())
        self.assertEqual(self.followup(copies=2).count("supercook-planner"), 1)

    def test_steps_that_are_not_owed_stay_silent(self):
        write_ledger(self.root, "run", ledger([
            "- [x] implement slice by slice: supercook-implementer (Task, composer-2.5)",
            "- [~] plan.md names the data shape: supercook-planner skip: tier trivial",
            "- [!] journey tests land red: supercook-test-designer blocked: waiting on design approval",
            "- [ ] the feature works end to end: supercook-verifier skip: no commits",
            "- [ ] the feature works end to end: supercook-verifier inline (spawn none)",
            "- [ ] open one PR per slice (yours), per references/deliver.md",
            "- [ ] triage every comment (yours; a code fix is a supercook-implementer launch you check)",
            "  - [ ] fix the in-scope findings: supercook-implementer, one launch",
        ]))
        self.assertEqual(self.run_hook(), {})

    def test_an_open_step_of_yours_is_passed_over_for_the_next_worker_step(self):
        write_ledger(self.root, "run", ledger([
            "- [ ] reproduce it and put the real failure output in the ledger (yours)",
            "- [ ] find the root cause with evidence: supercook-explorer scoped to the failing path",
        ]))
        self.assertIn("supercook-explorer scoped to the failing path", self.followup())

    def test_worker_lines_outside_the_steps_section_are_ignored(self):
        text = ledger([]) + "\n## Notes\n- [ ] later: supercook-implementer, maybe\n"
        write_ledger(self.root, "run", text)
        self.assertEqual(self.run_hook(), {})

    def test_no_run_ledger_is_silent(self):
        (self.root / ".supercook").mkdir()
        (self.root / ".supercook" / "ledger.md").write_text(ledger(), encoding="utf-8")
        self.assertEqual(self.run_hook(), {})

    def test_two_ledgers_without_a_matching_pointer_are_silent(self):
        write_ledger(self.root, "older", ledger())
        write_ledger(self.root, "newer", ledger())
        self.assertEqual(self.run_hook(), {})
        pointer = self.root / ".supercook" / "active-run"
        pointer.write_text(".supercook/missing/ledger.md\n", encoding="utf-8")
        self.assertEqual(self.run_hook(), {})
        pointer.write_bytes(b"\xff\xfe\xfd")
        self.assertEqual(self.run_hook(), {})

    def test_active_run_picks_between_several_ledgers(self):
        write_ledger(self.root, "older", ledger([STEPS[4]]))
        write_ledger(self.root, "newer", ledger())
        (self.root / ".supercook" / "active-run").write_text(".supercook/older/ledger.md\n", encoding="utf-8")
        message = self.followup()
        self.assertIn("supercook-implementer", message)
        self.assertNotIn("supercook-planner", message)

    def test_bad_input_and_other_events_print_an_empty_object(self):
        write_ledger(self.root, "run", ledger())
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
