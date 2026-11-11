"""Event-log journeys for hooks/cloud_roster_guard.py.

Event JSON on stdin, or argv doctor to print SUPERCOOK_HOOK_LOG. postToolUse prints
{"additional_context": ...} or {}. beforeSubmitPrompt prints {}. Exit 0. One doctor
line: {event} tool={name|-} then subagent_type name conversation_id
parent_conversation_id parent_agent_id parent_tool_call_id transcript_path, each
=yes or =no. yes is a non-empty string. On a Task line, subagent_type and name
also count inside tool_input. Null and empty are no. Values are omitted.
"""

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

# discover -s hooks puts this directory on sys.path. Importing as hooks.test_* does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_cloud_roster_edit_gate import (
    OWED,
    PARENT_AGENT,
    PARENT_CALL,
    PARENT_CONV,
    TRANSCRIPT,
    WORKER_CONV,
    pre_tool,
    tree,
)

REPO = Path(__file__).resolve().parent.parent
GUARD = REPO / "hooks" / "cloud_roster_guard.py"
PRESENCE = (
    "subagent_type", "name", "conversation_id", "parent_conversation_id",
    "parent_agent_id", "parent_tool_call_id", "transcript_path")
BANNED = (PARENT_CONV, WORKER_CONV, PARENT_AGENT, PARENT_CALL, TRANSCRIPT,
          "type-subagent-VALUE", "name-worker-VALUE", "conv-owner-VALUE")


def log_line(event_name, tool, present):
    flags = " ".join(f"{key}={'yes' if key in present else 'no'}" for key in PRESENCE)
    return f"{event_name} tool={tool or '-'} {flags}"


def task_return(root):
    return {
        "hook_event_name": "postToolUse", "conversation_id": PARENT_CONV,
        "session_id": PARENT_CONV, "model": "claude-opus-5-5", "tool_name": "Task",
        "tool_output": "worker finished the map", "workspace_roots": [str(root)],
        "transcript_path": TRANSCRIPT,
        "tool_input": {
            "description": "Map the hooks", "prompt": "Map the hooks folder.",
            "model": "composer-2.5", "subagent_type": "supercook-explorer",
        },
    }


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

    def assert_note(self, payload, *needles):
        self.assertEqual(set(payload), {"additional_context"}, payload)
        note = payload["additional_context"]
        self.assertIsInstance(note, str)
        for needle in ("relaunch", "fresh", "model", *needles):
            self.assertIn(needle, note, note)
        self.assertIsNone(re.search(r"\bresume\b", note, re.IGNORECASE), note)

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

    def test_post_tool_use_after_explorer_names_relaunch(self):
        with tree("plan") as root:
            self.assert_note(self.hook(root, task_return(root)), "supercook-explorer", OWED["plan"])

    def test_post_tool_use_without_a_ledger_still_names_relaunch(self):
        with tree() as root:
            self.assert_note(
                self.hook(root, task_return(root)), "supercook-explorer", "investigation", "read-only",
            )

    def test_post_tool_use_on_a_non_launch_is_silent(self):
        with tree("recon") as root:
            samples = (
                ("Shell", "parent", {"command": "omitted", "cwd": str(root)}),
                ("Read", "worker", {"file_path": str(root / "README.md")}),
                ("Grep", "worker", {"pattern": "ledger", "file_path": str(root)}),
                ("Write", "worker", {"file_path": str(root / "src" / "app.py")}),
            )
            for tool, shape, tool_input in samples:
                with self.subTest(tool=tool, shape=shape):
                    event = pre_tool(root, tool=tool, path="unused", key="path", shape=shape)
                    event["hook_event_name"] = "postToolUse"
                    event["tool_input"] = tool_input
                    event["tool_output"] = "omitted"
                    self.assertEqual(self.hook(root, event), {})

    def test_before_submit_prompt_is_logged_and_allowed(self):
        with tree() as root:
            secret_conv, secret_transcript = "conv-submit-VALUE", "/logs/transcript-submit-VALUE.jsonl"
            event = {
                "hook_event_name": "beforeSubmitPrompt", "conversation_id": secret_conv,
                "session_id": "session-submit-VALUE", "transcript_path": secret_transcript,
                "workspace_roots": [str(root)], "prompt": "start the run",
            }
            self.assertEqual(self.hook(root, event), {})
            line = log_line("beforeSubmitPrompt", None, {"conversation_id", "transcript_path"})
            self.assert_recorded(root, [line], [secret_conv, secret_transcript, "session-submit-VALUE"])
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["hook-log.txt"])

    def test_doctor_records_which_identity_fields_were_present(self):
        with tree() as root:
            product = str(root / "src" / "app.py")
            parent = pre_tool(root, tool="Write", path=product, key="path", shape="parent")
            worker = pre_tool(root, tool="StrReplace", path=product, key="file_path", shape="worker")
            worker.update({
                "subagent_type": "type-subagent-VALUE", "name": "name-worker-VALUE",
                "parent_conversation_id": "conv-owner-VALUE",
            })
            empty = pre_tool(root, tool="Delete", path=product, key="path", shape="parent")
            empty.update({key: "" for key in PRESENCE})
            # Unknown edit tools are allowed by the gate. Doctor still records tool=Edit.
            edit = pre_tool(root, tool="Edit", path=product, key="path", shape="parent")
            for event in (parent, worker, empty, edit):
                self.hook(root, event)
            parent_line = log_line("preToolUse", "Write", {"conversation_id", "transcript_path"})
            worker_line = log_line("preToolUse", "StrReplace", set(PRESENCE) - {"transcript_path"})
            empty_line = log_line("preToolUse", "Delete", set())
            edit_line = log_line("preToolUse", "Edit", {"conversation_id", "transcript_path"})
            self.assert_recorded(
                root, [parent_line, worker_line, empty_line, edit_line], BANNED,
            )

    def test_doctor_reads_launch_fields_from_tool_input(self):
        with tree() as root:
            launched = pre_tool(root, tool="Task", path="unused", key="path", shape="parent")
            launched["tool_input"] = {
                "description": "Map the hooks", "prompt": "Map the hooks folder.",
                "subagent_type": "supercook-explorer", "name": "supercook-explorer",
            }
            self.assertNotIn("subagent_type", launched)
            self.assertNotIn("name", launched)
            started = {
                "hook_event_name": "subagentStart", "subagent_type": "supercook-explorer",
                "workspace_roots": [str(root)],
            }
            self.assertNotIn("tool_input", started)
            bare = pre_tool(root, tool="Task", path="unused", key="path", shape="parent")
            bare["tool_input"] = {
                "description": "Map the hooks", "prompt": "Map the hooks folder.",
            }
            for event in (launched, started, bare):
                self.hook(root, event)
            parent_ids = {"conversation_id", "transcript_path"}
            launch_line = log_line(
                "preToolUse", "Task", parent_ids | {"subagent_type", "name"},
            )
            start_line = log_line("subagentStart", None, {"subagent_type"})
            bare_line = log_line("preToolUse", "Task", parent_ids)
            self.assert_recorded(
                root, [launch_line, start_line, bare_line], (*BANNED, "supercook-explorer"),
            )
