"""Edit-gate journeys for hooks/cloud_roster_guard.py.

preToolUse event JSON on stdin. Prints {"permission": "allow"} or
{"permission": "deny", "agent_message": ...} (user_message may equal
agent_message). Exit 0. No followup_message.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUARD = REPO / "hooks" / "cloud_roster_guard.py"
PHASES = ("assess", "recon", "plan", "test-first", "implement", "verify")
PARENT_CONV, WORKER_CONV = "conv-parent-VALUE", "conv-worker-VALUE"
PARENT_AGENT, PARENT_CALL = "agent-parent-VALUE", "call-parent-VALUE"
TRANSCRIPT = "/logs/transcript-parent-VALUE.jsonl"
SCHEMA = ("listed type", "free value", "name field", "general-purpose")
OWED = {"recon": "supercook-explorer", "plan": "supercook-planner",
        "test-first": "supercook-test-designer", "implement": "supercook-implementer"}


def ledger(open_from):
    opened = False
    rows = []
    for label in PHASES:
        opened = opened or label == open_from
        state = "not started" if opened else "done"
        rows.append(f"- [{' ' if opened else 'x'}] {label}: {state}")
    return (
        "# Ledger: edit gate fixture\nrun-id: fixture-run\n"
        "started: 2026-11-09 21:30 | tier: standard | track: bugfix\n\n## Phases\n"
        + "\n".join(rows) + "\n- [ ] deliver\n"
    )


def write_ledger(root, text):
    path = root / ".supercook" / "run" / "ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def pre_tool(root, *, tool, path, key, shape):
    # Parent: no parent_agent_id, transcript set. Worker: both parent ids, transcript null.
    parent = shape == "parent"
    event = {
        "hook_event_name": "preToolUse", "tool_name": tool, "tool_input": {key: path},
        "workspace_roots": [str(root)],
        "session_id": PARENT_CONV if parent else WORKER_CONV,
        "conversation_id": PARENT_CONV if parent else WORKER_CONV,
        "transcript_path": TRANSCRIPT if parent else None,
    }
    if not parent:
        event["parent_agent_id"] = PARENT_AGENT
        event["parent_tool_call_id"] = PARENT_CALL
    return event


@contextmanager
def tree(phase=None):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        if phase:
            write_ledger(root, ledger(phase))
        yield root


class CloudRosterEditGateTests(unittest.TestCase):
    def spawn(self, root, stdin):
        done = subprocess.run(
            [sys.executable, str(GUARD)], input=stdin, capture_output=True,
            text=True, timeout=10, cwd=root,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        return done

    def hook(self, root, event):
        done = self.spawn(root, json.dumps(event))
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            self.fail(f"stdout is not JSON: {done.stdout!r}")

    def edit(self, phase, tool, key, shape):
        with tree(phase) as root:
            event = pre_tool(root, tool=tool, path=str(root / "src" / "app.py"), key=key, shape=shape)
            return self.hook(root, event)

    def assert_allow(self, payload):
        self.assertEqual(payload, {"permission": "allow"}, payload)

    def assert_deny(self, payload, worker):
        self.assertEqual(payload.get("permission"), "deny", payload)
        message = payload.get("agent_message")
        self.assertIsInstance(message, str, payload)
        if "user_message" in payload:
            self.assertEqual(payload["user_message"], message)
        self.assertNotIn("followup_message", payload)
        self.assertIn(worker, message, message)
        for phrase in SCHEMA:
            self.assertIn(phrase, message, message)
        for sentence in re.split(r"[.!?\n]+", message):
            if re.search(r"\bcustom\b", sentence):
                self.assertIn("free value", sentence, sentence)
                self.assertIn("name field", sentence, sentence)

    def test_product_write_during_recon_is_denied(self):
        cases = (
            ("Write", "path", "parent"), ("Write", "file_path", "worker"),
            ("StrReplace", "path", "worker"), ("ApplyPatch", "target_file", "parent"),
            ("Delete", "path", "worker"), ("EditNotebook", "file_path", "parent"),
        )
        for tool, key, shape in cases:
            with self.subTest(tool=tool, key=key, shape=shape):
                self.assert_deny(self.edit("recon", tool, key, shape), OWED["recon"])

    def test_supercook_write_during_recon_is_allowed(self):
        with tree("recon") as root:
            path = root / ".supercook" / "run" / "ledger.md"
            for key in ("path", "file_path"):
                with self.subTest(key=key):
                    event = pre_tool(root, tool="Write", path=str(path), key=key, shape="parent")
                    self.assert_allow(self.hook(root, event))

    def test_worker_product_write_during_test_first_is_allowed(self):
        self.assert_allow(self.edit("test-first", "Write", "file_path", "worker"))

    def test_worker_product_write_during_implement_is_allowed(self):
        self.assert_allow(self.edit("implement", "Write", "file_path", "worker"))

    def test_parent_product_write_during_test_first_is_denied(self):
        self.assert_deny(self.edit("test-first", "Write", "path", "parent"), OWED["test-first"])

    def test_parent_product_write_during_implement_is_denied(self):
        for marker in ("omit", None, ""):
            with self.subTest(parent_agent_id=marker):
                with tree("implement") as root:
                    event = pre_tool(
                        root, tool="Write", path=str(root / "src" / "app.py"), key="path", shape="parent",
                    )
                    if marker != "omit":
                        event["parent_agent_id"] = marker
                    self.assert_deny(self.hook(root, event), OWED["implement"])

    def test_missing_parent_agent_id_with_null_transcript_during_implement_is_allowed(self):
        for transcript in (None, ""):
            with self.subTest(transcript=transcript):
                with tree("implement") as root:
                    event = pre_tool(
                        root, tool="Write", path=str(root / "src" / "app.py"), key="path", shape="parent",
                    )
                    event["transcript_path"] = transcript
                    self.assert_allow(self.hook(root, event))

    def test_parent_shell_during_implement_is_allowed(self):
        with tree("implement") as root:
            event = pre_tool(root, tool="Shell", path="unused", key="path", shape="parent")
            event["tool_input"] = {"command": "omitted", "cwd": str(root), "timeout": 30000}
            self.assert_allow(self.hook(root, event))

    def test_unknown_edit_tool_during_recon_is_allowed(self):
        self.assert_allow(self.edit("recon", "Edit", "path", "parent"))

    def test_product_write_with_no_ledger_is_allowed(self):
        with tree() as root:
            misplaced = root / ".supercook" / "ledger.md"
            misplaced.parent.mkdir(parents=True)
            misplaced.write_text(ledger("recon"), encoding="utf-8")
            event = pre_tool(root, tool="Write", path=str(root / "src" / "app.py"), key="path", shape="parent")
            self.assert_allow(self.hook(root, event))

    def test_parent_edit_with_undecodable_active_run_is_allowed(self):
        # Invalid UTF-8 in the pointer: read_text raises before any ledger is chosen.
        with tree() as root:
            for name in ("older", "newer"):
                path = root / ".supercook" / name / "ledger.md"
                path.parent.mkdir(parents=True)
                path.write_text(ledger("recon"), encoding="utf-8")
            (root / ".supercook" / "active-run").write_bytes(b"\xff\xfe\xfd")
            event = pre_tool(
                root, tool="Write", path=str(root / "src" / "app.py"), key="path", shape="parent",
            )
            self.assert_allow(self.hook(root, event))

    def test_guard_failure_allows_and_does_not_follow_up(self):
        with tree("recon") as root:
            event = {
                "hook_event_name": "preToolUse", "tool_name": "Write", "tool_input": "not-an-object",
                "workspace_roots": [1], "conversation_id": PARENT_CONV, "session_id": PARENT_CONV,
                "transcript_path": TRANSCRIPT,
            }
            self.assert_allow(self.hook(root, event))
