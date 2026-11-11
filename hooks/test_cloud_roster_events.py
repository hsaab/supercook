"""Event-log journeys for hooks/cloud_roster_guard.py.

Event JSON on stdin, or argv doctor to print SUPERCOOK_HOOK_LOG. Every non-stop
event prints {} and exits 0. One doctor line per event: {event} tool={name|-} then
subagent_type name conversation_id parent_conversation_id parent_agent_id
parent_tool_call_id transcript_path, each =yes or =no. yes is a non-empty string.
On a Task line, subagent_type and name also count inside tool_input. Null and
empty are no. Values are omitted.
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

REPO = Path(__file__).resolve().parent.parent
GUARD = REPO / "hooks" / "cloud_roster_guard.py"
PRESENCE = (
    "subagent_type", "name", "conversation_id", "parent_conversation_id",
    "parent_agent_id", "parent_tool_call_id", "transcript_path")
PARENT_CONV = "conv-parent-VALUE"
TRANSCRIPT = "/logs/transcript-parent-VALUE.jsonl"
BANNED = (PARENT_CONV, TRANSCRIPT, "type-subagent-VALUE", "name-worker-VALUE", "conv-owner-VALUE")


def log_line(event_name, tool, present):
    flags = " ".join(f"{key}={'yes' if key in present else 'no'}" for key in PRESENCE)
    return f"{event_name} tool={tool or '-'} {flags}"


def task_event(root, tool_input, **extra):
    event = {
        "hook_event_name": "postToolUse", "tool_name": "Task",
        "conversation_id": PARENT_CONV, "transcript_path": TRANSCRIPT,
        "workspace_roots": [str(root)], "tool_input": tool_input,
    }
    event.update(extra)
    return event


class CloudRosterEventTests(unittest.TestCase):
    def spawn(self, root, extra, stdin):
        env = os.environ.copy()
        env["SUPERCOOK_HOOK_LOG"] = str(root / "hook-log.txt")
        done = subprocess.run(
            [sys.executable, str(GUARD), *extra], input=stdin, capture_output=True,
            text=True, timeout=10, cwd=root, env=env,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        return done

    def hook(self, root, event):
        done = self.spawn(root, [], json.dumps(event))
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            self.fail(f"stdout is not JSON: {done.stdout!r}")

    def assert_recorded(self, root, lines, banned):
        done = self.spawn(root, ["doctor"], "")
        log_path = root / "hook-log.txt"
        log = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
        cursor = -1
        for line in lines:
            found = log.find(line, cursor + 1)
            detail = f"missing {line!r} in log {log!r}; doctor stdout {done.stdout!r}"
            self.assertGreater(found, cursor, detail)
            cursor = found
            self.assertIn(line, done.stdout, done.stdout)
        for secret in banned:
            self.assertNotIn(secret, log, log)
            self.assertNotIn(secret, done.stdout, done.stdout)

    def test_task_return_prints_an_empty_object_and_is_logged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            event = task_event(root, {
                "description": "Map the hooks", "prompt": "Map the hooks folder.",
                "model": "composer-2.5", "subagent_type": "supercook-explorer",
            })
            self.assertEqual(self.hook(root, event), {})
            line = log_line("postToolUse", "Task", {"conversation_id", "transcript_path", "subagent_type"})
            self.assert_recorded(root, [line], (*BANNED, "supercook-explorer"))

    def test_doctor_reads_launch_fields_from_tool_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            launched = task_event(root, {
                "description": "Map the hooks", "prompt": "Map the hooks folder.",
                "subagent_type": "supercook-explorer", "name": "supercook-explorer",
            })
            started = {
                "hook_event_name": "subagentStart", "subagent_type": "supercook-explorer",
                "workspace_roots": [str(root)],
            }
            bare = task_event(root, {"description": "Map the hooks", "prompt": "Map the hooks folder."})
            for event in (launched, started, bare):
                self.hook(root, event)
            parent_ids = {"conversation_id", "transcript_path"}
            lines = [
                log_line("postToolUse", "Task", parent_ids | {"subagent_type", "name"}),
                log_line("subagentStart", None, {"subagent_type"}),
                log_line("postToolUse", "Task", parent_ids),
            ]
            self.assert_recorded(root, lines, (*BANNED, "supercook-explorer"))

    def test_doctor_records_which_identity_fields_were_present(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            worker = task_event(root, {"prompt": "x"}, conversation_id="conv-worker-VALUE")
            worker.update({
                "transcript_path": None, "parent_agent_id": "agent-parent-VALUE",
                "parent_tool_call_id": "call-parent-VALUE",
                "parent_conversation_id": "conv-owner-VALUE",
                "subagent_type": "type-subagent-VALUE", "name": "name-worker-VALUE",
            })
            empty = task_event(root, {"prompt": "x"})
            empty.update({key: "" for key in PRESENCE})
            for event in (worker, empty):
                self.hook(root, event)
            lines = [
                log_line("postToolUse", "Task", set(PRESENCE) - {"transcript_path"}),
                log_line("postToolUse", "Task", set()),
            ]
            self.assert_recorded(root, lines, (*BANNED, "conv-worker-VALUE", "agent-parent-VALUE"))


if __name__ == "__main__":
    unittest.main()
