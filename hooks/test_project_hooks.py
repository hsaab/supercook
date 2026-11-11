"""Project hook registration for .cursor/hooks.json.

The project registers two entries, both on hooks/cloud_roster_guard.py: the stop
followup and a Task postToolUse that only feeds the event log. The plugin ships
no hooks. Run: python3 -m unittest hooks.test_project_hooks
"""

import json
import sys
import unittest
from pathlib import Path

# discover -s hooks puts this directory on sys.path. Importing as hooks.test_* does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parent.parent
PROJECT_HOOKS = REPO / ".cursor" / "hooks.json"
PLUGIN_MANIFEST = REPO / ".cursor-plugin" / "plugin.json"
GUARD_COMMAND = "python3 hooks/cloud_roster_guard.py"


class ProjectHooksTests(unittest.TestCase):
    def project_hooks(self):
        if not PROJECT_HOOKS.is_file():
            self.fail(".cursor/hooks.json does not exist")
        payload = json.loads(PROJECT_HOOKS.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("version"), 1)
        hooks = payload.get("hooks")
        self.assertIsInstance(hooks, dict, payload)
        return hooks

    def test_stop_hook_runs_the_guard_with_a_short_loop_limit(self):
        stop = self.project_hooks().get("stop") or []
        self.assertEqual(len(stop), 1, stop)
        self.assertEqual(stop[0].get("command"), GUARD_COMMAND)
        self.assertEqual(stop[0].get("loop_limit"), 2)

    def test_post_tool_use_logs_task_launches_only(self):
        post = self.project_hooks().get("postToolUse") or []
        self.assertEqual(len(post), 1, post)
        self.assertEqual(post[0].get("command"), GUARD_COMMAND)
        self.assertEqual(post[0].get("matcher"), "Task")

    def test_project_registers_nothing_that_can_deny_a_tool_or_a_launch(self):
        hooks = self.project_hooks()
        self.assertEqual(sorted(hooks), ["postToolUse", "stop"], hooks)
        text = PROJECT_HOOKS.read_text(encoding="utf-8")
        self.assertNotIn("enforce_roster", text)
        self.assertNotIn("${CURSOR_PLUGIN_ROOT}", text)

    def test_plugin_ships_no_hooks(self):
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        self.assertNotIn("hooks", manifest)
        self.assertFalse((REPO / "hooks" / "hooks.json").exists())


if __name__ == "__main__":
    unittest.main()
