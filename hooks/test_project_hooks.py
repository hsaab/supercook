"""Project hook registration for .cursor/hooks.json.

A parent registers subagentStart, Task preToolUse, and the stop hook.
The guard is also on preToolUse and postToolUse with no matcher, and on
beforeSubmitPrompt.
Run: python3 -m unittest hooks.test_project_hooks
"""

import json
import sys
import unittest
from pathlib import Path

# discover -s hooks puts this directory on sys.path. Importing as hooks.test_* does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parent.parent
PROJECT_HOOKS = REPO / ".cursor" / "hooks.json"
PLUGIN_HOOKS = REPO / "hooks" / "hooks.json"
ROSTER_COMMAND = "python3 hooks/enforce_roster.py"
GUARD_COMMAND = "python3 hooks/cloud_roster_guard.py"


class ProjectHooksTests(unittest.TestCase):
    def project_hooks(self):
        if not PROJECT_HOOKS.is_file():
            self.fail(".cursor/hooks.json does not exist")
        return json.loads(PROJECT_HOOKS.read_text(encoding="utf-8"))

    def assert_command(
        self, hooks, event, command, matcher=None, loop_limit=None, absent_matcher=False,
    ):
        found = [entry for entry in (hooks.get(event) or [])]
        for entry in found:
            if entry.get("command") != command:
                continue
            # "no matcher key" is not the same as a matcher whose value is null.
            if absent_matcher and "matcher" in entry:
                continue
            if matcher is not None and entry.get("matcher") != matcher:
                continue
            if loop_limit is not None and entry.get("loop_limit") != loop_limit:
                continue
            return
        matcher_pin = "no matcher key" if absent_matcher else f"matcher {matcher!r}"
        self.fail(
            f"{event} missing {command!r} {matcher_pin} loop_limit {loop_limit!r} in {found!r}"
        )

    def assert_subagent_start_roster(self, hooks):
        # subagentStart matches the subagent type. "Task" is a tool name and never fires.
        found = list(hooks.get("subagentStart") or [])
        roster = [entry for entry in found if entry.get("command") == ROSTER_COMMAND]
        if not roster:
            self.fail(f"subagentStart missing {ROSTER_COMMAND!r} in {found!r}")
        for entry in roster:
            if "matcher" not in entry or entry["matcher"] == "supercook-.*":
                return
        self.fail(
            f"subagentStart {ROSTER_COMMAND!r} must omit matcher or set it to "
            f"'supercook-.*' (matcher 'Task' would never fire) in {roster!r}"
        )

    def test_project_hooks_register_subagent_start_task_and_stop(self):
        payload = self.project_hooks()
        self.assertEqual(payload.get("version"), 1)
        hooks = payload.get("hooks")
        self.assertIsInstance(hooks, dict, payload)
        self.assert_subagent_start_roster(hooks)
        self.assert_command(hooks, "preToolUse", ROSTER_COMMAND, matcher="Task")
        self.assert_command(hooks, "stop", GUARD_COMMAND, loop_limit=5)

    def test_project_hooks_do_not_use_plugin_root_or_task_v2(self):
        plugin_text = PLUGIN_HOOKS.read_text(encoding="utf-8")
        plugin = json.loads(plugin_text)
        self.assertNotIn("stop", plugin["hooks"])
        self.assertNotIn("cloud_roster_guard.py", plugin_text)
        if not PROJECT_HOOKS.is_file():
            self.fail(".cursor/hooks.json does not exist")
        text = PROJECT_HOOKS.read_text(encoding="utf-8")
        self.assertNotIn("${CURSOR_PLUGIN_ROOT}", text)
        self.assertNotIn("task_v2", text)

    def test_project_hooks_register_the_guard_on_every_tool_event(self):
        payload = self.project_hooks()
        hooks = payload.get("hooks")
        self.assertIsInstance(hooks, dict, payload)
        gaps = []
        pins = (
            ("preToolUse", True),
            ("postToolUse", True),
            ("beforeSubmitPrompt", False),
        )
        for event, absent_matcher in pins:
            try:
                self.assert_command(
                    hooks, event, GUARD_COMMAND, absent_matcher=absent_matcher,
                )
            except AssertionError as error:
                gaps.append(str(error))
        if gaps:
            self.fail("\n".join(gaps))


if __name__ == "__main__":
    unittest.main()
