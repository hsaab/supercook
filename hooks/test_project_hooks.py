"""Hook registration: this repo registers one stop hook; the plugin ships none.

Run: python3 -m unittest discover -s hooks
"""

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROJECT_HOOKS = REPO / ".cursor" / "hooks.json"
PLUGIN_MANIFEST = REPO / ".cursor-plugin" / "plugin.json"


class ProjectHooksTests(unittest.TestCase):
    def test_project_registers_only_the_stop_followup(self):
        payload = json.loads(PROJECT_HOOKS.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("version"), 1)
        hooks = payload.get("hooks")
        self.assertEqual(sorted(hooks), ["stop"], hooks)
        self.assertEqual(len(hooks["stop"]), 1, hooks)
        stop = hooks["stop"][0]
        self.assertEqual(stop.get("command"), "python3 hooks/ledger_followup.py")
        self.assertEqual(stop.get("loop_limit"), 2)
        self.assertTrue((REPO / "hooks" / "ledger_followup.py").is_file())

    def test_plugin_ships_no_hooks(self):
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        self.assertNotIn("hooks", manifest)
        self.assertFalse((REPO / "hooks" / "hooks.json").exists())


if __name__ == "__main__":
    unittest.main()
