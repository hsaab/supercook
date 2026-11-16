"""Journeys for scripts/launch_log.py, the postToolUse hook that logs each launch that returned.

Run: python3 -m unittest discover -s scripts
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import launch_log

HOOK = Path(launch_log.__file__).resolve()
AGENT_ID = "505ca07f-2ee1-5226-be4a-e765ba70548b"


class LaunchLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.run = self.root / ".supercook" / "run"
        self.run.mkdir(parents=True)
        (self.run / "ledger.md").write_text("# Ledger\n\n## Steps\n", encoding="utf-8")
        (self.root / ".supercook" / "active-run").write_text(".supercook/run/ledger.md\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def fire(self, tool_name="Task", tool_input=None, tool_output=None, stdin_text=None):
        if stdin_text is None:
            stdin_text = json.dumps({
                "hook_event_name": "postToolUse",
                "tool_name": tool_name,
                "tool_input": tool_input if tool_input is not None else {"subagent_type": "supercook-explorer"},
                "tool_output": tool_output if tool_output is not None else json.dumps({"agentId": f"bc-{AGENT_ID}"}),
                "tool_use_id": "toolu_1",
                "workspace_roots": [str(self.root)],
            })
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=stdin_text, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), {})

    def rows(self):
        path = self.run / "launches.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def test_a_returned_typed_launch_is_logged_with_role_model_and_agent_id(self):
        self.fire(tool_input={"subagent_type": "supercook-implementer", "model": "composer-2.5", "description": "slice 1"})
        (row,) = self.rows()
        self.assertEqual(
            {key: row[key] for key in ("role", "model", "agent_id", "tool_use_id")},
            {"role": "supercook-implementer", "model": "composer-2.5", "agent_id": AGENT_ID, "tool_use_id": "toolu_1"},
        )

    def test_the_agent_id_is_found_in_text_output_too(self):
        self.fire(tool_output=f"done\n\nAgent ID: bc-{AGENT_ID} (resume with this id)")
        self.assertEqual(self.rows()[0]["agent_id"], AGENT_ID)

    def test_a_general_purpose_launch_through_call_dynamic_tool_logs_the_agent_file_role(self):
        arguments = json.dumps({"subagent_type": "generalPurpose", "prompt": "Follow /p/agents/supercook-verifier.md."})
        self.fire(tool_name="CallDynamicTool", tool_input={"namespace": "cursor", "toolName": "Task", "arguments": arguments})
        self.assertEqual(self.rows()[0]["role"], "supercook-verifier")

    def test_other_tools_other_agents_and_finished_runs_log_nothing(self):
        self.fire(tool_name="Shell", tool_input={"command": "ls"})
        self.fire(tool_name="CallDynamicTool", tool_input={"toolName": "WebFetch", "arguments": "{}"})
        self.fire(tool_input={"subagent_type": "generalPurpose", "prompt": "Summarize agents/supercook-implementer.md"})
        self.fire(tool_input={"subagent_type": "explore", "prompt": "Follow /p/agents/supercook-implementer.md"})
        (self.root / ".supercook" / "active-run").unlink()
        self.fire()
        self.assertEqual(self.rows(), [])

    def test_a_symlinked_log_is_never_written_through(self):
        target = self.root / "bashrc"
        target.write_text("# rc\n", encoding="utf-8")
        (self.run / "launches.jsonl").symlink_to(target)
        self.fire(tool_input={"subagent_type": "supercook-explorer", "description": "$(touch pwned)"})
        self.assertEqual(target.read_text(encoding="utf-8"), "# rc\n")

    def test_bad_input_or_an_unwritable_log_prints_an_empty_object(self):
        for stdin_text in ("not json", "[]", json.dumps({"hook_event_name": "postToolUse", "tool_name": "Task"})):
            with self.subTest(stdin=stdin_text):
                self.fire(stdin_text=stdin_text)
        (self.run / "launches.jsonl").mkdir()
        self.fire()


if __name__ == "__main__":
    unittest.main()
