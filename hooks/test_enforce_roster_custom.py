"""Custom-name launches and subagentStart decisions for hooks/enforce_roster.py.

Run with: python3 -m unittest discover hooks
subagentStart cases are built by HookTestCase.check_start, keyed by hook_event_name.
"""

import json
import tempfile
import unittest
from pathlib import Path

# Shared helpers and base only: importing a TestCase that has tests would run them twice.
from test_enforce_roster import ALLOW, Case, HookTestCase, LEDGER, OMIT, SHIPPED, tags

HOST_MODEL = "grok-4.7-high"
ARENA_B_FALLBACK = ((LEDGER, "models: arena-b inherit (unavailable composer-2.5)\n"),)


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
        self.check_start([
            Case(
                "custom implementer, no tags",
                "",
                SHIPPED["implementer"],
                "custom",
                ("deny", "supercook-role", "supercook-run"),
                name="supercook-implementer",
            ),
        ])

    def test_subagent_start_custom_without_name_is_allowed(self):
        self.check_start([
            Case("custom helper, no name", "Objective: map the hooks folder.", OMIT, "custom", ALLOW),
        ])

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
        self.check_start([
            Case(label, task, model, "supercook-implementer", expect, subagent_model=subagent_model)
            for label, model, subagent_model, expect in directions
        ])

    def test_subagent_start_deny_sets_user_message(self):
        roster_model = SHIPPED["implementer"]
        denied = self.check_start([
            Case(
                "untagged subagentStart",
                "",
                roster_model,
                "supercook-implementer",
                ("deny", "supercook-role", "supercook-run"),
            ),
        ])[0]
        self.assertTrue(denied.get("agent_message"), denied)
        self.assertTrue(denied.get("user_message"), denied)
        self.assertEqual(denied.get("user_message"), denied.get("agent_message"))

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

        allowed = self.check_start([
            Case("allow", tags("implementer"), roster_model, "supercook-implementer", ALLOW),
        ])[0]
        self.assertEqual(allowed.get("permission"), "allow", allowed)
        self.assertNotIn("user_message", allowed)

    def test_subagent_start_inherit_role_allows_the_host_model(self):
        self.check_start([
            Case(
                "inherit arena-a, host model",
                tags("arena-a"),
                HOST_MODEL,
                "supercook-arena-runner",
                ALLOW,
                subagent_model=HOST_MODEL,
            ),
        ])

    def test_subagent_start_ledger_fallback_allows_the_host_model(self):
        self.check_start([
            Case(
                "ledger fallback arena-b, host model",
                tags("arena-b"),
                HOST_MODEL,
                "supercook-arena-runner",
                ALLOW,
                ARENA_B_FALLBACK,
                subagent_model=HOST_MODEL,
            ),
        ])

    def test_subagent_start_empty_tool_input_still_requires_tags(self):
        self.check_start([
            Case(
                "subagentStart with empty tool_input",
                "",
                OMIT,
                "supercook-implementer",
                ("deny", "supercook-role", "supercook-run"),
                subagent_model=SHIPPED["implementer"],
                tool_input={},
            ),
        ])


if __name__ == "__main__":
    unittest.main()
