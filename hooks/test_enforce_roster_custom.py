"""Custom-name launches and subagentStart decisions for hooks/enforce_roster.py.

Run with: python3 -m unittest discover hooks
subagentStart cases send a top-level body with no tool_input.
"""

import json
import tempfile
import unittest
from pathlib import Path

# Shared base only: importing a TestCase that has tests would run them twice.
from test_enforce_roster import ALLOW, Case, HookTestCase, OMIT, SHIPPED, tags


class CustomLaunchTests(HookTestCase):
    def test_custom_name_without_tags_is_denied(self):
        self.check([
            Case(
                "custom implementer, no tags",
                tags(run=None),
                SHIPPED["implementer"],
                "custom",
                ("deny", "supercook-role", "supercook-run"),
                name="supercook-implementer",
            ),
        ])

    def test_custom_name_with_tags_and_roster_model_is_allowed(self):
        self.check([
            Case(
                "custom implementer, both tags, roster model",
                tags("implementer"),
                SHIPPED["implementer"],
                "custom",
                ALLOW,
                name="supercook-implementer",
            ),
        ])

    def test_custom_name_with_wrong_model_is_denied(self):
        self.check([
            Case(
                "custom implementer, wrong model",
                tags("implementer"),
                "claude-opus-5-5-high",
                "custom",
                ("deny", SHIPPED["implementer"]),
                name="supercook-implementer",
            ),
        ])

    def test_custom_name_missing_run_tag_is_denied(self):
        self.check([
            Case(
                "custom implementer, role and no run",
                tags("implementer", run=None),
                SHIPPED["implementer"],
                "custom",
                ("deny", "supercook-run"),
                name="supercook-implementer",
            ),
        ])

    def test_custom_foreign_name_is_allowed(self):
        self.check([
            Case("custom helper, no tags", tags(run=None), "composer-2.5", "custom", ALLOW, name="my-helper"),
        ])

    def test_subagent_start_name_without_tags_is_denied(self):
        payload = {
            "subagent_type": "custom",
            "name": "supercook-implementer",
            "model": SHIPPED["implementer"],
            "task": "",
        }
        with tempfile.TemporaryDirectory() as temp:
            response = self.run_hook(Path(temp), json.dumps(payload))
        message = response.get("agent_message", "")
        seen = (response.get("permission"), *(part for part in ("supercook-role", "supercook-run") if part in message))
        self.assertEqual(seen, ("deny", "supercook-role", "supercook-run"), response)

    def test_subagent_start_custom_without_name_is_allowed(self):
        payload = {"subagent_type": "custom", "task": "Objective: map the hooks folder."}
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.run_hook(Path(temp), json.dumps(payload)), {"permission": "allow"})

    def test_subagent_start_uses_subagent_model(self):
        roster_model = SHIPPED["implementer"]
        wrong = "claude-opus-5-5-high"
        task = tags("implementer")
        directions = (
            ("roster subagent_model, empty top-level model", "", roster_model, ALLOW),
            ("roster subagent_model, wrong top-level model", wrong, roster_model, ALLOW),
            ("wrong subagent_model, roster top-level model", roster_model, wrong, ("deny", roster_model)),
            ("top-level roster model only", roster_model, OMIT, ALLOW),
        )
        for label, model, subagent_model, expect in directions:
            with self.subTest(label), tempfile.TemporaryDirectory() as temp:
                payload = {
                    "hook_event_name": "subagentStart",
                    "subagent_type": "supercook-implementer",
                    "model": model,
                    "task": task,
                }
                if subagent_model is not OMIT:
                    payload["subagent_model"] = subagent_model
                response = self.run_hook(Path(temp), json.dumps(payload))
                message = response.get("agent_message", "")
                seen = (response.get("permission"), *(part for part in expect[1:] if part in message))
                self.assertEqual(seen, expect, response)

    def test_subagent_start_deny_sets_user_message(self):
        roster_model = SHIPPED["implementer"]
        with self.subTest("untagged subagentStart"), tempfile.TemporaryDirectory() as temp:
            payload = {
                "hook_event_name": "subagentStart",
                "subagent_type": "supercook-implementer",
                "model": roster_model,
                "task": "",
            }
            response = self.run_hook(Path(temp), json.dumps(payload))
            agent_message = response.get("agent_message") or ""
            user_message = response.get("user_message") or ""
            self.assertEqual(response.get("permission"), "deny", response)
            self.assertIn("supercook-role", agent_message)
            self.assertIn("supercook-run", agent_message)
            self.assertTrue(agent_message, response)
            self.assertTrue(user_message, response)
            self.assertEqual(user_message, agent_message)

        with self.subTest("preToolUse deny"), tempfile.TemporaryDirectory() as temp:
            payload = {
                "hook_event_name": "preToolUse",
                "tool_name": "Subagent",
                "tool_input": {
                    "description": "launch",
                    "prompt": "",
                    "subagent_type": "supercook-implementer",
                    "model": roster_model,
                },
            }
            response = self.run_hook(Path(temp), json.dumps(payload))
            self.assertEqual(response.get("permission"), "deny", response)
            self.assertTrue(response.get("agent_message"), response)
            self.assertNotIn("user_message", response)

        with self.subTest("allow"), tempfile.TemporaryDirectory() as temp:
            payload = {
                "hook_event_name": "subagentStart",
                "subagent_type": "supercook-implementer",
                "model": roster_model,
                "task": tags("implementer"),
            }
            response = self.run_hook(Path(temp), json.dumps(payload))
            self.assertEqual(response.get("permission"), "allow", response)
            self.assertNotIn("user_message", response)


if __name__ == "__main__":
    unittest.main()
