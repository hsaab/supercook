"""Journeys for scripts/audit_runs.py. Run: python3 -m unittest discover -s scripts

Each test writes transcripts in the shape Cursor stores under
~/.cursor/projects/<project>/agent-transcripts/<chat>/<chat>.jsonl and audits them.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_runs

SCRIPT = Path(audit_runs.__file__).resolve()
STALE_SHA = "437267fc85a0c0b69fb9056bad92f2364b76f93a"


def fake_plugin(home: Path, relative_root: str, version: str) -> str:
    """Create a plugin root with a manifest and return the SKILL.md path a chat would attach."""
    root = home / relative_root
    (root / ".cursor-plugin").mkdir(parents=True)
    (root / ".cursor-plugin" / "plugin.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    return str(root / "skills" / "supercook" / "SKILL.md")


def attach(skill_path: str) -> dict:
    text = f"<manually_attached_skills>\nSkill Name: supercook\nPath: {skill_path}\nSKILL.md content:\n# Supercook"
    return {"role": "user", "message": {"content": [{"type": "text", "text": text}]}}


def say(text: str) -> dict:
    return {"role": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def call(name: str, tool_input) -> dict:
    return {"role": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": tool_input}]}}


def write_chat(root: Path, project: str, chat: str, entries: list, extra_lines=()) -> Path:
    path = root / project / "agent-transcripts" / chat / f"{chat}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(entry) for entry in entries] + list(extra_lines)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class AuditRunsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.projects = self.home / "projects"
        self.stale_skill = fake_plugin(
            self.home, f"plugins/cache/supercook-marketplace/supercook/{STALE_SHA}", "0.1.0"
        )
        self.local_skill = fake_plugin(self.home, "plugins/local/supercook", "0.5.0")

    def tearDown(self):
        self.temp.cleanup()

    def stale_run(self) -> Path:
        """The fc27 shape: old skill, a dynamic Task launch with string arguments, a hook block, a parent edit."""
        launch = json.dumps({"subagent_type": "supercook-verifier", "model": "inherit", "prompt": "verify"})
        return write_chat(self.projects, "crate", "chat-stale", [
            attach(self.stale_skill),
            call("CallDynamicTool", {"namespace": "cursor", "toolName": "Task", "arguments": launch}),
            say("Launching supercook-verifier was blocked by a preToolUse hook, so verify runs inline."),
            call("StrReplace", {"path": "/repo/src/app.ts", "old_string": "a", "new_string": "b"}),
            call("Write", {"path": "/repo/.supercook/run/ledger.md", "contents": "# Ledger"}),
        ])

    def test_stale_install_run_reports_version_denial_and_parent_edit(self):
        row = audit_runs.audit_chat(self.stale_run())
        self.assertEqual(row["skills"][0]["install"], "cache@437267f")
        self.assertEqual(row["skills"][0]["version"], "0.1.0")
        self.assertEqual(row["launches"], {"supercook-verifier": 1})
        self.assertEqual(row["hook_denials"], 1)
        self.assertIn("preToolUse hook", row["denial_example"])
        self.assertEqual(row["product_edits"], ["/repo/src/app.ts"])

    def test_typed_and_fallback_launches_are_counted_by_worker(self):
        patch = "*** Begin Patch\n*** Update File: /repo/src/b.ts\n@@\n-a\n+b\n*** End Patch"
        path = write_chat(self.projects, "green-machine", "chat-local", [
            attach(self.local_skill),
            call("Task", {"subagent_type": "supercook-explorer", "prompt": "map auth"}),
            call("Task", {"subagent_type": "supercook-explorer", "prompt": "map api", "run_in_background": True}),
            call("Subagent", {"subagent_type": "generalPurpose",
                              "prompt": "Read /p/agents/supercook-verifier.md and follow it."}),
            call("Task", {"subagent_type": "explore", "prompt": "unrelated"}),
            call("ApplyPatch", patch),
        ])
        row = audit_runs.audit_chat(path)
        self.assertEqual(row["skills"][0], {"path": self.local_skill, "install": "local", "version": "0.5.0"})
        self.assertEqual(row["launches"], {
            "explore": 1, "generalPurpose:supercook-verifier": 1, "supercook-explorer": 2,
        })
        self.assertEqual(row["hook_denials"], 0)
        self.assertEqual(row["product_edits"], ["/repo/src/b.ts"])

    def test_every_documented_launch_shape_counts_as_its_role_and_a_mere_mention_does_not(self):
        launch = json.dumps({"subagent_type": "supercook-planner", "prompt": "plan"})
        path = write_chat(self.projects, "crate", "chat-shapes", [
            attach(self.local_skill),
            call("Task", {"subagent_type": "custom", "name": "supercook-implementer", "prompt": "slice 1"}),
            call("Task", {"subagent_type": "generalPurpose", "description": "supercook-verifier: audit",
                          "prompt": "<agent file body>"}),
            call("Task", {"subagent_type": "generalPurpose",
                          "prompt": "Read `/p/agents/supercook-test-designer.md` and follow it."}),
            call("CallDynamicTool", {"namespace": "cursor", "toolName": "Task", "arguments": launch}),
            call("Task", {"subagent_type": "explore", "prompt": "Read /p/agents/supercook-implementer.md"}),
            call("Task", {"subagent_type": "generalPurpose", "prompt": "Summarize agents/supercook-implementer.md"}),
        ])
        row = audit_runs.audit_chat(path)
        self.assertEqual(row["launches"], {
            "custom:supercook-implementer": 1, "explore": 1, "generalPurpose": 1,
            "generalPurpose:supercook-test-designer": 1, "generalPurpose:supercook-verifier": 1,
            "supercook-planner": 1,
        })

    def test_solo_runs_are_left_out_of_the_launch_counts(self):
        ledger = "capabilities: git yes | spawn none | parent-host cloud-agent"
        solo = audit_runs.audit_chat(write_chat(self.projects, "crate", "chat-solo", [
            attach(self.local_skill),
            call("Write", {"path": "/repo/.supercook/run/ledger.md", "contents": ledger}),
            call("StrReplace", {"path": "/repo/src/e.ts", "old_string": "a", "new_string": "b"}),
        ]))
        self.assertTrue(solo["solo"])
        summary = audit_runs.summarize([solo, audit_runs.audit_chat(self.stale_run())])
        self.assertEqual(summary["solo_runs"], 1)
        self.assertEqual(summary["no_supercook_launch"], 0)
        self.assertEqual(summary["parent_edits_without_implementer"], 1)

    def test_the_announced_version_wins_over_the_copy_on_disk(self):
        row = audit_runs.audit_chat(write_chat(self.projects, "crate", "chat-said", [
            attach(self.local_skill), say("supercook 0.4.2 from ~/.cursor/plugins/local/supercook\nStarting."),
        ]))
        self.assertEqual(row["announced_version"], "0.4.2")
        self.assertEqual(audit_runs.summarize([row])["installs"], {"local 0.4.2": 1})

    def test_a_skill_path_under_the_home_folder_finds_its_manifest(self):
        with mock.patch.dict(os.environ, {"HOME": str(self.home)}):
            self.assertEqual(audit_runs.plugin_version("~/plugins/local/supercook/skills/supercook/SKILL.md"), "0.5.0")

    def test_negated_hook_mentions_are_not_denials(self):
        row = audit_runs.audit_chat(write_chat(self.projects, "crate", "chat-negated", [
            attach(self.local_skill),
            say("This repo's stop hook does not deny edits or launches. The hook didn't block the launch either."),
        ]))
        self.assertEqual(row["hook_denials"], 0)

    def test_edits_through_call_dynamic_tool_are_counted(self):
        row = audit_runs.audit_chat(write_chat(self.projects, "crate", "chat-dynamic", [
            attach(self.local_skill),
            call("CallDynamicTool", {"namespace": "cursor", "toolName": "Delete",
                                     "arguments": {"path": "/repo/src/old.ts"}}),
        ]))
        self.assertEqual(row["product_edits"], ["/repo/src/old.ts"])

    def test_short_paths_missing_files_and_list_manifests_do_not_crash(self):
        (self.home / "s.jsonl").write_text(json.dumps(attach(self.local_skill)) + "\n", encoding="utf-8")
        done = subprocess.run(
            [sys.executable, str(SCRIPT), "missing.jsonl", "s.jsonl", "--json"],
            capture_output=True, text=True, timeout=30, cwd=self.home,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("skipped missing.jsonl", done.stderr)
        self.assertEqual([chat["project"] for chat in json.loads(done.stdout)["chats"]], [""])
        listed = fake_plugin(self.home, "plugins/local/listed", "0.5.0")
        (Path(listed).parents[2] / ".cursor-plugin" / "plugin.json").write_text("[]", encoding="utf-8")
        self.assertIsNone(audit_runs.plugin_version(listed))

    def test_chats_without_the_skill_and_subagent_transcripts_are_skipped(self):
        self.stale_run()
        write_chat(self.projects, "crate", "chat-plain", [say("no skill here")])
        nested = self.projects / "crate" / "agent-transcripts" / "chat-stale" / "subagents" / "x.jsonl"
        nested.parent.mkdir(parents=True)
        nested.write_text(json.dumps(attach(self.stale_skill)) + "\n", encoding="utf-8")
        chats = audit_runs.collect(audit_runs.iter_transcripts(self.projects))
        self.assertEqual([chat["chat"] for chat in chats], ["chat-stale"])

    def test_malformed_lines_do_not_stop_the_audit(self):
        path = write_chat(self.projects, "crate", "chat-broken", [
            attach(self.local_skill), call("Task", {"subagent_type": "supercook-implementer", "prompt": "x"}),
        ], extra_lines=("not json", "[]"))
        self.assertEqual(audit_runs.audit_chat(path)["launches"], {"supercook-implementer": 1})

    def test_summary_counts_runs_where_the_parent_edited_without_an_implementer(self):
        stale = audit_runs.audit_chat(self.stale_run())
        silent = audit_runs.audit_chat(write_chat(self.projects, "crate", "chat-silent", [
            attach(self.stale_skill), call("Write", {"path": "/repo/src/c.ts", "contents": "x"}),
        ]))
        delegated = audit_runs.audit_chat(write_chat(self.projects, "crate", "chat-delegated", [
            attach(self.local_skill),
            call("Task", {"subagent_type": "supercook-implementer", "prompt": "slice 1"}),
            call("StrReplace", {"path": "/repo/src/d.ts", "old_string": "a", "new_string": "b"}),
        ]))
        summary = audit_runs.summarize([stale, silent, delegated])
        self.assertEqual(summary["chats"], 3)
        self.assertEqual(summary["installs"], {"cache@437267f 0.1.0": 2, "local 0.5.0": 1})
        self.assertEqual(summary["no_supercook_launch"], 1)
        self.assertEqual(summary["implementer_launched"], 1)
        self.assertEqual(summary["parent_edits_without_implementer"], 2)
        self.assertEqual(summary["hook_denials_mentioned"], 1)

    def test_cli_prints_json_and_honors_since(self):
        old = self.stale_run()
        write_chat(self.projects, "crate", "chat-new", [attach(self.local_skill)])
        os.utime(old, (0, 0))
        done = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.projects), "--since", "2000-01-01", "--json"],
            capture_output=True, text=True, timeout=30, cwd=self.home,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual([chat["chat"] for chat in report["chats"]], ["chat-new"])
        self.assertEqual(report["summary"]["no_supercook_launch"], 1)

    def test_cli_text_report_names_the_install_and_the_totals(self):
        self.stale_run()
        done = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.projects)],
            capture_output=True, text=True, timeout=30, cwd=self.home,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("skill: cache@437267f 0.1.0", done.stdout)
        self.assertIn("launches: verifier 1", done.stdout)
        self.assertIn("parent edits without implementer: 1", done.stdout)


if __name__ == "__main__":
    unittest.main()
