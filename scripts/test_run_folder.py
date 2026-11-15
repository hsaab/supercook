"""The ledger check and live-run lookup in scripts/run_folder.py, tested in process.

Run: python3 -m unittest discover -s scripts
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_folder

ID_A = "7c1e4b52-9d0a-4f3e-8a21-5b6d0c9e1f34"
ID_B = "2f8b3a60-14c7-4d95-b0e2-97a1c5d3e801"
HEADER = "# Ledger\ntier: standard | track: feature | big-change: no\nspawn: typed | tests: `make test`\n"
MAP = "map the code: supercook-explorer, a broad launch then one per area"
PLAN = "plan.md: supercook-planner, or three supercook-arena-runner launches then supercook-plan-judge"
IMPLEMENT = "implement slice by slice: supercook-implementer, one launch per slice"
VERIFY = "the feature works end to end: supercook-verifier, a fresh launch"


def ledger(*rows: str, header: str = HEADER) -> str:
    return f"{header}\n## Steps\n" + "\n".join(rows) + "\n\n## Log\n- 09:14 assess\n"


def launched(*roles: str, agent_id: str | None = None) -> list[dict]:
    return [{"role": role, "agent_id": agent_id} for role in roles]


class LedgerProblems(unittest.TestCase):
    """Each case: ledger rows, logged launches, and the fragments the problems must contain (none means clean)."""

    CASES = [
        ("a checked step with a launch of its role is clean",
         [f"- [x] {MAP}"], launched("supercook-explorer"), []),
        ("any role the step names vouches for it",
         [f"- [x] {PLAN}"], launched("supercook-plan-judge"), []),
        ("a launch of another role does not vouch for the step",
         [f"- [x] {MAP}"], launched("supercook-verifier"), ["checked with no logged launch or agent id: step 1"]),
        ("a recorded agent id vouches for its row with or without a log",
         [f"- [x] {MAP} (Task {ID_A})"], [], []),
        ("one implementer launch does not cover two slices",
         [f"- [ ] {IMPLEMENT}", "  - [x] slice 1: types", "  - [x] slice 2: bucket"],
         launched("supercook-implementer"), ["checked with no logged launch or agent id: step 1.2"]),
        ("a launch already claimed by an agent id on another row is not reused",
         [f"- [ ] {IMPLEMENT}", f"  - [x] slice 1: types (Task {ID_B})", "  - [x] slice 2: bucket"],
         launched("supercook-implementer", agent_id=f"bc-{ID_B}"), ["step 1.2"]),
        ("the review track's nested worker row is checked",
         ["- [ ] for each PR, bottom-up:", "  - [ ] launch the reviewers",
          "  - [x] fix the in-scope findings: supercook-implementer, one launch"],
         [], ["checked with no logged launch or agent id: step 1.2"]),
        ("an uppercase X is a checked row",
         [f"- [X] {VERIFY}"], [], ["checked with no logged launch or agent id: step 1"]),
        ("implement and verify are never skipped",
         [f"- [~] {IMPLEMENT} skip: tier standard", f"- [ ] {VERIFY} skip: no commits"], [],
         ["never skipped, launch the worker: step 1", "never skipped, launch the worker: step 2"]),
        ("a skip citing this run's tier, big-change, or a scope modifier is clean",
         [f"- [~] {MAP} skip: tier standard", f"- [~] {PLAN} skip: big-change no", "- [~] tests: supercook-test-designer skip: plan only"],
         [], []),
        ("a skip citing another tier or no reason it may use is flagged",
         [f"- [~] {MAP} skip: tier trivial", f"- [~] {PLAN} skip: it looked small"], [],
         ["a skip must cite this run's tier", "step 2"]),
        ("a nested review row may skip with no findings",
         ["- [ ] for each PR:", "  - [~] fix the in-scope findings: supercook-implementer skip: no findings"], [], []),
        ("a skipped mark needs a skip reason",
         [f"- [~] {MAP} (did it myself)"], [], ["marked skipped with no skip: reason: step 1"]),
        ("inline is flagged unless the run has spawn: none",
         [f"- [x] {MAP} inline (launch failed: timeout)"], [], ["inline is only for spawn: none, launch the worker: step 1"]),
        ("the first open worker step is cited by number",
         ["- [ ] reproduce it (yours)", f"- [ ] {MAP}", f"- [ ] {VERIFY}"], [], ["still open: step 2: map the code"]),
        ("rows outside ## Steps are ignored",
         [], [], []),
    ]

    def test_cases(self):
        for name, rows, launches, expected in self.CASES:
            with self.subTest(name):
                found = "\n".join(run_folder.problems(ledger(*rows), launches))
                if not expected:
                    self.assertEqual(found, "")
                for fragment in expected:
                    self.assertIn(fragment, found)

    def test_inline_is_clean_under_spawn_none(self):
        header = HEADER.replace("spawn: typed", "spawn: none")
        self.assertEqual(run_folder.problems(ledger(f"- [x] {MAP} inline (spawn none)", header=header), []), [])

    def test_a_long_step_is_clipped_in_the_message(self):
        (message,) = run_folder.problems(ledger(f"- [ ] {MAP} {'x' * 500}"), [])
        self.assertLess(len(message), run_folder.ECHO_CHARS + 40)

    def test_a_notes_section_after_the_steps_is_ignored(self):
        text = ledger() + "\n## Notes\n- [ ] later: supercook-implementer, maybe\n"
        self.assertEqual(run_folder.problems(text, []), [])


class LiveRun(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.run = self.root / ".supercook" / "run"
        self.run.mkdir(parents=True)
        (self.run / "ledger.md").write_text(ledger(f"- [ ] {MAP}"), encoding="utf-8")
        self.pointer = self.root / ".supercook" / "active-run"

    def tearDown(self):
        self._tmp.cleanup()

    def point(self, target=".supercook/run/ledger.md"):
        self.pointer.write_text(target + "\n", encoding="utf-8")

    def test_a_run_without_active_run_is_finished_and_ignored(self):
        self.assertIsNone(run_folder.run_ledger([self.root]))
        self.point()
        self.assertEqual(run_folder.run_ledger([self.root, self.root]), self.run / "ledger.md")

    def test_a_pointer_git_tracks_came_with_a_clone_and_is_ignored(self):
        self.point()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", ".supercook/active-run"], cwd=self.root, check=True)
        self.assertIsNone(run_folder.run_ledger([self.root]))

    def test_a_pointer_outside_the_run_folders_is_ignored(self):
        outside = self.root / "elsewhere" / "ledger.md"
        outside.parent.mkdir()
        outside.write_text(ledger(f"- [ ] {MAP}"), encoding="utf-8")
        self.point("elsewhere/ledger.md")
        self.assertIsNone(run_folder.run_ledger([self.root]))

    def test_a_symlinked_run_folder_is_ignored(self):
        real = self.root / "real-run"
        real.mkdir()
        (real / "ledger.md").write_text(ledger(), encoding="utf-8")
        (self.root / ".supercook" / "linked").symlink_to(real)
        self.point(".supercook/linked/ledger.md")
        self.assertIsNone(run_folder.run_ledger([self.root]))

    def test_two_live_runs_across_roots_are_ambiguous(self):
        self.point()
        other = Path(tempfile.mkdtemp(dir=self.root))
        (other / ".supercook" / "b").mkdir(parents=True)
        (other / ".supercook" / "b" / "ledger.md").write_text(ledger(), encoding="utf-8")
        (other / ".supercook" / "active-run").write_text(".supercook/b/ledger.md", encoding="utf-8")
        self.assertIsNone(run_folder.run_ledger([self.root, other]))

    def test_launch_rows_are_deduplicated_by_tool_use_id(self):
        rows = ['{"role": "supercook-explorer", "tool_use_id": "t1"}'] * 2 + ['{"role": "supercook-explorer"}', "junk"]
        (self.run / "launches.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
        self.assertEqual(len(run_folder.read_launches(self.run / "ledger.md")), 2)


if __name__ == "__main__":
    unittest.main()
