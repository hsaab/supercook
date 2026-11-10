"""User-journey tests for hooks/enforce_roster.py. Run with: python3 -m unittest discover hooks

Each case pipes a real-shaped preToolUse payload through the hook script in a fresh temp tree with HOME inside it.
subagentStart cases send a top-level body with no tool_input.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import NamedTuple

# discover -s hooks puts this directory on sys.path. Importing the module as hooks.test_enforce_roster does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import enforce_roster
import roster

HOOK_SCRIPT = Path(enforce_roster.__file__).resolve()
SHIPPED = roster.parse_roster((HOOK_SCRIPT.parent.parent / "skills/supercook/models.md").read_text(encoding="utf-8"))
OMIT = object()


def models_file(*roster_lines):
    return "# Model preferences\n\n## The roster\n\n```\n" + "\n".join(roster_lines) + "\n```\n"


HOME_MODELS = models_file("standard:  home-standard", "explorer:  home-explorer   # pick", "reviewer:  home-reviewer", "arena-a:   inherit")
FALLBACK_LEDGER = "# Ledger\nrun-id: x\nmodels: explorer home-explorer | arena-b inherit (unavailable gpt-5.6-sol-max)\n"
REPO_MODELS, FIRST_MODELS, LEDGER = "repo/.supercook/models.md", "first/.supercook/models.md", "repo/run/ledger.md"
BUGBOT = "Full Repository Path: /workspace/repo\nDiff: branch changes\nCustom Instructions: focus on hooks/.\n"
ALLOW = ("allow",)
OMITTED_DENY = ("deny", SHIPPED["arena-b"], "inherit (unavailable")
FALLBACK = ((LEDGER, FALLBACK_LEDGER),)


def tags(role=None, run="{run}", body="Objective: map the hooks folder."):
    """Prompt with line-anchored tags; {run} and {root} are filled per case."""
    lines = ([f"supercook-role: {role}"] if role else []) + ([f"supercook-run: {run}"] if run else [])
    return "\n".join([*lines, "", body])


class Case(NamedTuple):
    label: str
    prompt: str
    model: object
    subagent_type: str
    expect: tuple
    files: tuple = ()
    roots: tuple | None = ("repo",)
    name: str = ""


def match_and_mismatch(name, prompt, subagent_type, expected, wrong, files=(), roots=("repo",)):
    """The expected slug is allowed and a wrong slug is denied with the expected slug named."""
    return [
        Case(f"{name}: expected", prompt, expected, subagent_type, ALLOW, files, roots),
        Case(f"{name}: wrong", prompt, wrong, subagent_type, ("deny", expected), files, roots),
    ]


class HookTestCase(unittest.TestCase):
    def run_hook(self, root, stdin_text):
        env = {**os.environ, "HOME": str(root / "home")}
        done = subprocess.run([sys.executable, str(HOOK_SCRIPT)], input=stdin_text, capture_output=True, text=True, timeout=10, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def check(self, cases):
        for case in cases:
            with self.subTest(case.label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                (root / "repo" / "run").mkdir(parents=True)
                for rel, text in (("home/.supercook/models.md", HOME_MODELS), *case.files):
                    (root / rel).parent.mkdir(parents=True, exist_ok=True)
                    (root / rel).write_text(text, encoding="utf-8")
                tool_input = {
                    "description": "launch", "run_in_background": False,
                    "prompt": case.prompt.format(run=root / "repo" / "run", root=root),
                    "subagent_type": case.subagent_type,
                    **({} if case.model is OMIT else {"model": case.model}),
                    **({} if case.name == "" else {"name": case.name}),
                }
                roots = {} if case.roots is None else {"workspace_roots": [str(root / name) for name in case.roots]}
                response = self.run_hook(root, json.dumps({"tool_name": "Subagent", "tool_input": tool_input, **roots}))
                seen = (response.get("permission"), *(p for p in case.expect[1:] if p in response.get("agent_message", "")))
                self.assertEqual(seen, case.expect, response)


class LaunchDecisionTests(HookTestCase):
    def test_tagged_launch_is_allowed_only_with_the_roster_model(self):
        self.check([
            *match_and_mismatch("explorer", tags("explorer"), "supercook-explorer", "home-explorer", "composer-2.5"),
            Case("implementer falls to shipped", tags("implementer"), SHIPPED["implementer"], "supercook-implementer", ALLOW),
            Case("test designer tags standard", tags("standard"), "home-standard", "supercook-test-designer", ALLOW),
            *match_and_mismatch("bugbot uses the reviewer role", BUGBOT + tags("reviewer"), "bugbot", "home-reviewer", "composer-2.5"),
        ])

    def test_unknown_role_is_denied_listing_valid_roles_and_inherit_role_requires_an_omitted_model(self):
        self.check([
            Case("unknown role", tags("test-designer"), "home-standard", "supercook-test-designer", ("deny", *sorted(roster.ROSTER_KEYS))),
            Case("inherit role, model omitted", tags("arena-a"), OMIT, "supercook-arena-runner", ALLOW),
            Case("inherit role, model passed", tags("arena-a"), "claude-opus-5-5-high", "supercook-arena-runner", ("deny",)),
        ])

    def test_untagged_supercook_launch_is_denied_asking_for_both_tags_and_untagged_foreign_launch_is_allowed(self):
        prompts = {"no tags": tags(run=None), "run tag only": tags(), "inline role": "Use supercook-role: explorer later."}
        foreign = (("explore", "composer-2.5"), ("generalPurpose", OMIT), ("bugbot", "anything"))
        self.check([
            *(Case(n, p, "home-explorer", "supercook-explorer", ("deny", "supercook-role", "supercook-run")) for n, p in prompts.items()),
            *(Case(kind, tags(run=None), model, kind, ALLOW) for kind, model in foreign),
        ])

    def test_omitted_model_is_allowed_only_for_an_announced_ledger_fallback(self):
        ledgers = {
            "no ledger file": None,
            "malformed fallback entry": "models: arena-b inherit (unavailable\n",
            "plain inherit entry": "models: arena-b inherit | explorer home-explorer\n",
            "fallback for another role": "models: arena-c inherit (unavailable gpt-5.6-sol-max)\n",
            "no models header": "# Ledger\n## Log\n- arena-b inherit (unavailable gpt-5.6-sol-max)\n",
        }
        arena_b = tags("arena-b")
        self.check([
            Case("announced fallback", arena_b, OMIT, "supercook-arena-runner", ALLOW, FALLBACK),
            Case("fallback but wrong model", arena_b, "gpt-5.6-sol-max", "supercook-arena-runner", ("deny", SHIPPED["arena-b"]), FALLBACK),
            *(Case(n, arena_b, OMIT, "supercook-arena-runner", OMITTED_DENY, ((LEDGER, t),) if t else ()) for n, t in ledgers.items()),
        ])

    def test_supercook_launch_with_role_but_no_run_is_denied(self):
        self.check([
            Case("role without run", tags("explorer", run=None), "home-explorer", "supercook-explorer", ("deny", "supercook-run")),
            Case("foreign role without run stays allowed", tags("explorer", run=None), "home-explorer", "explore", ALLOW),
        ])

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


class RosterSourceTests(HookTestCase):
    def test_repository_roster_beats_home_and_home_beats_shipped(self):
        repo_explorer = ((REPO_MODELS, models_file("explorer: repo-explorer")),)
        explorer, implementer = tags("explorer"), tags("implementer")
        self.check([
            *match_and_mismatch("repo names explorer", explorer, "supercook-explorer", "repo-explorer", "home-explorer", repo_explorer),
            *match_and_mismatch("repo names another role", explorer, "supercook-explorer", "home-explorer", "repo-explorer", ((REPO_MODELS, models_file("standard: repo-standard")),)),
            *match_and_mismatch("repo absent", explorer, "supercook-explorer", "home-explorer", "repo-explorer"),
            *match_and_mismatch("repo beats shipped", implementer, "supercook-implementer", "repo-implementer", SHIPPED["implementer"], ((REPO_MODELS, models_file("implementer: repo-implementer")),)),
            *match_and_mismatch("home and repo silent", implementer, "supercook-implementer", SHIPPED["implementer"], "repo-implementer"),
            *match_and_mismatch("roots missing", explorer, "supercook-explorer", "home-explorer", "repo-explorer", repo_explorer, None),
            *match_and_mismatch("roots empty", explorer, "supercook-explorer", "home-explorer", "repo-explorer", repo_explorer, ()),
        ])

    def test_repository_root_is_the_one_containing_the_run_folder_otherwise_the_first(self):
        files = ((FIRST_MODELS, models_file("explorer: first-explorer")), (REPO_MODELS, models_file("explorer: repo-explorer")))
        relative_ledger = (*files, ("first/.supercook/rel-run/ledger.md", FALLBACK_LEDGER))
        roots = ("first", "repo")
        self.check([
            *match_and_mismatch("run in second root", tags("explorer"), "supercook-explorer", "repo-explorer", "first-explorer", files, roots),
            *match_and_mismatch("run outside every root", tags("explorer", "{root}/elsewhere/run"), "supercook-explorer", "first-explorer", "repo-explorer", files, roots),
            *match_and_mismatch("no run tag", tags("explorer", None), "explore", "first-explorer", "repo-explorer", files, roots),
            Case("relative run resolves against first root", tags("arena-b", ".supercook/rel-run"), OMIT, "supercook-arena-runner", ALLOW, relative_ledger, roots),
        ])


class TagParsingTests(HookTestCase):
    def test_first_line_anchored_tags_win_including_inside_custom_instructions(self):
        decoy = "Never copy the inline text supercook-role: reviewer.\n" + tags("explorer", body="Example:\nsupercook-role: reviewer")
        two_runs = "supercook-role: arena-b\nsupercook-run: {}\nsupercook-run: {}\n"
        self.check([
            *match_and_mismatch("decoy role tags", decoy, "supercook-explorer", "home-explorer", "home-reviewer"),
            Case("first run tag picks the ledger", two_runs.format("{run}", "{root}/repo/other"), OMIT, "supercook-arena-runner", ALLOW, FALLBACK),
            Case("later run tag is ignored", two_runs.format("{root}/repo/other", "{run}"), OMIT, "supercook-arena-runner", OMITTED_DENY, FALLBACK),
            *match_and_mismatch("custom instructions role", BUGBOT + tags("explorer"), "security-review", "home-explorer", "home-reviewer"),
            Case("empty role line does not take the next line", "supercook-role:\nexplorer\nsupercook-run: {run}\n", "home-explorer", "supercook-explorer", ("deny",)),
            Case("empty run line does not take the next line", "supercook-role: arena-b\nsupercook-run:\n{run}\n", OMIT, "supercook-arena-runner", ("deny", "supercook-run"), FALLBACK),
        ])


class FailOpenTests(HookTestCase):
    def test_garbage_stdin_is_allowed_and_exits_zero(self):
        for stdin_text in ("not json at all", "", "[]", '{"tool_name": "Subagent"}', '{"tool_input": "a string"}'):
            with self.subTest(stdin=stdin_text), tempfile.TemporaryDirectory() as temp:
                self.assertEqual(self.run_hook(Path(temp), stdin_text), {"permission": "allow"})


if __name__ == "__main__":
    unittest.main()
