"""Every shipped hook config runs: the plugin's hooks.json, this repo's project hooks, and the README snippet.

Each command runs through `sh` the way Cursor runs it, against a live run in a temp workspace.
Run: python3 -m unittest discover -s scripts
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_folder

REPO = Path(__file__).resolve().parent.parent
PERMISSION_HOOKS = {"preToolUse", "subagentStart", "beforeShellExecution", "beforeMCPExecution", "beforeReadFile"}
LEDGER = "# Ledger\nspawn: typed\n\n## Steps\n- [ ] plan.md: supercook-planner\n"


def readme_snippet() -> dict:
    blocks = re.findall(r"^```json\n(.*?)^```", (REPO / "README.md").read_text(encoding="utf-8"), re.S | re.M)
    (snippet,) = [json.loads(block) for block in blocks if '"postToolUse"' in block]
    return snippet["hooks"]


class HookConfigs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.workspace = self.tmp / "workspace"
        (self.workspace / ".supercook" / "run").mkdir(parents=True)
        (self.workspace / ".supercook" / "run" / "ledger.md").write_text(LEDGER, encoding="utf-8")
        (self.workspace / ".supercook" / "active-run").write_text(".supercook/run/ledger.md", encoding="utf-8")
        self.home = self.tmp / "home"
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def configs(self):
        clone = self.home / ".cursor" / "plugins" / "local" / "supercook"
        clone.parent.mkdir(parents=True)
        clone.symlink_to(REPO)
        plugin = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        project = json.loads((REPO / ".cursor" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        return {
            "plugin": (plugin, self.workspace, {"CURSOR_PLUGIN_ROOT": str(REPO)}),
            "project": (project, REPO, {}),
            "readme": (readme_snippet(), self.workspace, {"HOME": str(self.home)}),
        }

    def run_command(self, command, event, cwd, env):
        done = subprocess.run(
            ["sh", "-c", command], input=json.dumps(event), capture_output=True, text=True,
            cwd=cwd, env={**os.environ, **env}, timeout=10,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_the_plugin_manifest_ships_the_hooks_file(self):
        manifest = json.loads((REPO / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["hooks"], "./hooks/hooks.json")

    def test_every_config_logs_returned_launches_and_nudges_at_stop_without_a_permission_hook(self):
        launch = {
            "hook_event_name": "postToolUse", "tool_name": "Task", "tool_use_id": "t1",
            "tool_input": {"subagent_type": "supercook-explorer"}, "tool_output": "{}",
            "workspace_roots": [str(self.workspace)],
        }
        stop = {"hook_event_name": "stop", "status": "completed", "workspace_roots": [str(self.workspace)]}
        for name, (hooks, cwd, env) in self.configs().items():
            with self.subTest(config=name):
                self.assertFalse(PERMISSION_HOOKS & set(hooks))
                (logger,) = hooks["postToolUse"]
                self.assertLessEqual(run_folder.LAUNCH_TOOLS | {"CallDynamicTool"}, set(logger["matcher"].split("|")))
                self.assertEqual(self.run_command(logger["command"], launch, cwd, env), {})
                (nudge,) = hooks["stop"]
                self.assertIn("still open: step 1", self.run_command(nudge["command"], stop, cwd, env)["followup_message"])
        logged = (self.workspace / ".supercook" / "run" / "launches.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(logged), 3)
        self.assertEqual(len(run_folder.read_launches(self.workspace / ".supercook" / "run" / "ledger.md")), 1)

    def test_the_readme_snippet_prints_an_empty_object_when_the_plugin_is_not_cloned(self):
        for hook in readme_snippet().values():
            with self.subTest(command=hook[0]["command"]):
                self.assertEqual(self.run_command(hook[0]["command"], {}, self.workspace, {"HOME": str(self.home)}), {})


if __name__ == "__main__":
    unittest.main()
