"""User-journey tests for the Subagent launch enforcement hook (hooks/enforce_roster.py).

Each test pipes a real-shaped preToolUse payload through the hook script with HOME
pointed at a temporary home, so the system tier never reads the developer's files.

Run with: python3 -m unittest discover hooks
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import enforce_roster
import roster

HOOK_SCRIPT = Path(enforce_roster.__file__).resolve()
SHIPPED_ROSTER = roster.parse_roster(
    (Path(__file__).resolve().parent.parent / "skills/supercook/models.md").read_text(encoding="utf-8")
)

OMIT = object()


def models_file(*roster_lines):
    body = "\n".join(roster_lines)
    return f"# Model preferences\n\n## The roster\n\n```\n{body}\n```\n"


HOME_ROSTER = models_file(
    "standard:  home-standard",
    "explorer:  home-explorer   # personal pick",
    "reviewer:  home-reviewer",
    "arena-a:   inherit",
)
ANNOUNCED_FALLBACK_LEDGER = (
    "# Ledger\nrun-id: x\nmodels: explorer home-explorer | arena-b inherit (unavailable gpt-5.6-sol-max)\n"
)


def tagged_prompt(role=None, run=None, body="Objective: map the hooks folder."):
    tags = ([f"supercook-role: {role}"] if role else []) + ([f"supercook-run: {run}"] if run else [])
    return "\n".join([*tags, "", body])


def bugbot_prompt(run, role="reviewer"):
    return (
        "Full Repository Path: /workspace/repo\nDiff: branch changes\n"
        f"Custom Instructions: focus on hooks/.\nsupercook-role: {role}\nsupercook-run: {run}"
    )


class HookTestCase(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name).resolve()
        self.home = self.root / "home"
        self.repo = self.root / "repo"
        self.run_folder = self.repo / ".supercook" / "2026-11-07-run"
        self.run_folder.mkdir(parents=True)
        self.write(self.home / ".supercook" / "models.md", HOME_ROSTER)

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_hook(self, stdin_text):
        completed = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT)],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "HOME": str(self.home)},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def launch(self, prompt, model=OMIT, subagent_type="supercook-explorer", roots="default"):
        tool_input = {"description": "launch", "prompt": prompt, "run_in_background": False}
        tool_input["subagent_type"] = subagent_type
        if model is not OMIT:
            tool_input["model"] = model
        payload = {"tool_name": "Subagent", "tool_input": tool_input}
        if roots != OMIT:
            payload["workspace_roots"] = [str(r) for r in ([self.repo] if roots == "default" else roots)]
        return self.run_hook(json.dumps(payload))

    def assert_decision(self, response, permission, *message_parts):
        self.assertEqual(response.get("permission"), permission, response)
        for part in message_parts:
            self.assertIn(part, response.get("agent_message", ""), response)


class TaggedLaunchTests(HookTestCase):
    def test_tagged_launch_is_allowed_only_with_the_roster_model(self):
        cases = [
            ("explorer passes its exact slug", "supercook-explorer", "explorer", "home-explorer", "allow", ()),
            ("explorer passes a wrong slug", "supercook-explorer", "explorer", "composer-2.5", "deny", ("home-explorer",)),
            ("explorer passes another role's slug", "supercook-explorer", "explorer", "home-reviewer", "deny", ("home-explorer",)),
            ("implementer falls to shipped", "supercook-implementer", "implementer", SHIPPED_ROSTER["implementer"], "allow", ()),
            ("test designer tags standard", "supercook-test-designer", "standard", "home-standard", "allow", ()),
        ]
        for name, subagent_type, role, model, permission, parts in cases:
            with self.subTest(name):
                response = self.launch(tagged_prompt(role, self.run_folder), model, subagent_type)
                self.assert_decision(response, permission, *parts)

    def test_tagged_foreign_review_agent_is_enforced_through_the_reviewer_role(self):
        for model, permission, parts in (("home-reviewer", "allow", ()), ("composer-2.5", "deny", ("home-reviewer",))):
            with self.subTest(model=model):
                response = self.launch(bugbot_prompt(self.run_folder), model, subagent_type="bugbot")
                self.assert_decision(response, permission, *parts)

    def test_unknown_role_is_denied_with_every_valid_role_listed(self):
        response = self.launch(tagged_prompt("test-designer", self.run_folder), "home-standard", "supercook-test-designer")
        self.assert_decision(response, "deny", *sorted(roster.ROSTER_KEYS))

    def test_inherit_role_allows_an_omitted_model_and_denies_a_passed_one(self):
        for model, permission in ((OMIT, "allow"), ("claude-opus-5-5-high", "deny")):
            with self.subTest(model="omitted" if model is OMIT else model):
                response = self.launch(tagged_prompt("arena-a", self.run_folder), model, "supercook-arena-runner")
                self.assert_decision(response, permission)


class UntaggedLaunchTests(HookTestCase):
    def test_untagged_supercook_launch_is_denied_and_asked_for_both_tags(self):
        prompts = {
            "no tags": tagged_prompt(),
            "run tag only": tagged_prompt(run=self.run_folder),
            "role mentioned mid line": "Objective: launch with supercook-role: explorer later.",
        }
        for name, prompt in prompts.items():
            with self.subTest(name):
                response = self.launch(prompt, "home-explorer", "supercook-explorer")
                self.assert_decision(response, "deny", "supercook-role", "supercook-run")

    def test_untagged_foreign_launch_is_allowed(self):
        for subagent_type, model in (("explore", "composer-2.5"), ("generalPurpose", OMIT), ("bugbot", "anything")):
            with self.subTest(subagent_type=subagent_type):
                self.assert_decision(self.launch(tagged_prompt(), model, subagent_type), "allow")


class LedgerFallbackTests(HookTestCase):
    def test_omitted_model_is_allowed_only_for_an_announced_ledger_fallback(self):
        cases = {
            "announced fallback": (ANNOUNCED_FALLBACK_LEDGER, OMIT, "allow"),
            "no ledger file": (None, OMIT, "deny"),
            "malformed fallback entry": ("models: arena-b inherit (unavailable\n", OMIT, "deny"),
            "plain inherit entry": ("models: arena-b inherit | explorer home-explorer\n", OMIT, "deny"),
            "fallback for another role": ("models: arena-c inherit (unavailable gpt-5.6-sol-max)\n", OMIT, "deny"),
            "no models header": ("# Ledger\n## Log\n- arena-b inherit (unavailable gpt-5.6-sol-max)\n", OMIT, "deny"),
            "announced fallback but a wrong model passed": (ANNOUNCED_FALLBACK_LEDGER, "composer-2.5", "deny"),
        }
        for name, (ledger_text, model, permission) in cases.items():
            with self.subTest(name):
                ledger_path = self.run_folder / "ledger.md"
                if ledger_text is None:
                    ledger_path.unlink(missing_ok=True)
                else:
                    self.write(ledger_path, ledger_text)
                response = self.launch(tagged_prompt("arena-b", self.run_folder), model, "supercook-arena-runner")
                parts = (SHIPPED_ROSTER["arena-b"],) if permission == "deny" else ()
                self.assert_decision(response, permission, *parts)

    def test_denied_omitted_model_explains_how_to_record_the_fallback(self):
        response = self.launch(tagged_prompt("arena-b", self.run_folder), OMIT, "supercook-arena-runner")
        self.assert_decision(response, "deny", "gpt-5.6-sol-max", "inherit (unavailable")


class RosterTierTests(HookTestCase):
    def test_repository_roster_beats_home_and_home_beats_shipped(self):
        repo_override = self.repo / ".supercook" / "models.md"
        cases = [
            ("repository names explorer", "explorer: repo-explorer", "explorer", "repo-explorer", "home-explorer"),
            ("repository names another role", "standard: repo-standard", "explorer", "home-explorer", "repo-explorer"),
            ("repository absent", None, "explorer", "home-explorer", "repo-explorer"),
            ("repository beats shipped", "implementer: repo-implementer", "implementer", "repo-implementer", "x"),
            ("home and repository silent", None, "implementer", SHIPPED_ROSTER["implementer"], "repo-implementer"),
        ]
        for name, override_line, role, expected, wrong in cases:
            with self.subTest(name):
                if override_line is None:
                    repo_override.unlink(missing_ok=True)
                else:
                    self.write(repo_override, models_file(override_line))
                prompt = tagged_prompt(role, self.run_folder)
                self.assert_decision(self.launch(prompt, expected, f"supercook-{role}"), "allow")
                self.assert_decision(self.launch(prompt, wrong, f"supercook-{role}"), "deny", expected)

    def test_missing_or_empty_workspace_roots_skips_the_repository_tier(self):
        self.write(self.repo / ".supercook" / "models.md", models_file("explorer: repo-explorer"))
        for roots in (OMIT, []):
            with self.subTest(roots="missing" if roots is OMIT else "empty"):
                response = self.launch(tagged_prompt("explorer", self.run_folder), "home-explorer", roots=roots)
                self.assert_decision(response, "allow")


class WorkspaceRootSelectionTests(HookTestCase):
    def setUp(self):
        super().setUp()
        self.first_root = self.root / "first"
        self.write(self.first_root / ".supercook" / "models.md", models_file("explorer: first-explorer"))
        self.write(self.repo / ".supercook" / "models.md", models_file("explorer: repo-explorer"))

    def test_repository_root_is_the_one_containing_the_run_folder_otherwise_the_first(self):
        cases = {
            "run folder in second root": (self.run_folder, "repo-explorer"),
            "run folder outside every root": (self.root / "elsewhere" / "run", "first-explorer"),
            "no run tag": (None, "first-explorer"),
        }
        for name, (run, expected) in cases.items():
            with self.subTest(name):
                roots = [self.first_root, self.repo]
                response = self.launch(tagged_prompt("explorer", run), expected, roots=roots)
                self.assert_decision(response, "allow")

    def test_relative_run_tag_resolves_against_the_first_root(self):
        self.write(self.first_root / ".supercook" / "rel-run" / "ledger.md", ANNOUNCED_FALLBACK_LEDGER)
        prompt = tagged_prompt("arena-b", ".supercook/rel-run")
        response = self.launch(prompt, OMIT, "supercook-arena-runner", roots=[self.first_root, self.repo])
        self.assert_decision(response, "allow")


class TagParsingTests(HookTestCase):
    def test_first_line_anchored_tags_win(self):
        prompt = (
            "Objective: never copy the inline text supercook-role: reviewer from examples.\n"
            "supercook-role: explorer\nsupercook-run: {run}\nQuoted example:\nsupercook-role: reviewer\n"
        ).format(run=self.run_folder)
        self.assert_decision(self.launch(prompt, "home-explorer"), "allow")
        self.assert_decision(self.launch(prompt, "home-reviewer"), "deny", "home-explorer")

    def test_first_run_tag_picks_the_ledger(self):
        other_run = self.repo / ".supercook" / "other-run"
        self.write(self.run_folder / "ledger.md", ANNOUNCED_FALLBACK_LEDGER)
        other_run.mkdir(parents=True)
        for first, second, permission in ((self.run_folder, other_run, "allow"), (other_run, self.run_folder, "deny")):
            with self.subTest(first=first.name):
                prompt = f"supercook-role: arena-b\nsupercook-run: {first}\nsupercook-run: {second}\n"
                self.assert_decision(self.launch(prompt, OMIT, "supercook-arena-runner"), permission)

    def test_tags_inside_custom_instructions_are_read(self):
        response = self.launch(bugbot_prompt(self.run_folder, role="explorer"), "home-explorer", "security-review")
        self.assert_decision(response, "allow")


class FailOpenTests(HookTestCase):
    def test_garbage_stdin_is_allowed_and_exits_zero(self):
        inputs = ["not json at all", "", "[]", '{"tool_name": "Subagent"}', '{"tool_input": "a string"}']
        for stdin_text in inputs:
            with self.subTest(stdin=stdin_text):
                self.assert_decision(self.run_hook(stdin_text), "allow")


if __name__ == "__main__":
    unittest.main()
