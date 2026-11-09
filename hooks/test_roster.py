"""User-journey tests for roster and ledger parsing (hooks/roster.py).

Run with: python3 -m unittest discover hooks
"""

import tempfile
import unittest
from pathlib import Path

import roster

SHIPPED_MODELS_PATH = Path(__file__).resolve().parent.parent / "skills/supercook/models.md"

ROSTER_KEYS = {
    "standard", "arena-a", "arena-b", "arena-c", "plan-judge",
    "plan-optimizer", "implementer", "explorer", "reviewer", "review-implementer",
}


def models_file(*roster_lines, preamble=""):
    """Build a models.md body shaped like the shipped file, with the given roster lines."""
    body = "\n".join(roster_lines)
    return f"# Model preferences\n\n{preamble}\n## The roster\n\n```\n{body}\n```\n\nTrailing prose.\n"


SHIPPED_FIXTURE = models_file(
    "standard:     shipped-standard   # assessor, planner, test-designer, verifier",
    "arena-a:      shipped-arena-a",
    "arena-b:      shipped-arena-b",
    "explorer:     shipped-explorer",
    "reviewer:     shipped-reviewer   # bugbot, security-review",
)

SHIPPED_FIXTURE_ROSTER = {
    "standard": "shipped-standard",
    "arena-a": "shipped-arena-a",
    "arena-b": "shipped-arena-b",
    "explorer": "shipped-explorer",
    "reviewer": "shipped-reviewer",
}

THIS_RUN_MODELS_HEADER = (
    "models: standard claude-opus-5-5-high | arena-a claude-fable-5-1-thinking-high"
    " | arena-b inherit (unavailable gpt-5.6-sol-max) | arena-c claude-opus-5-5-high"
    " | plan-judge claude-opus-5-5-high | plan-optimizer claude-opus-5-5-high"
    " | implementer composer-2.5 | explorer composer-2.5 | reviewer claude-opus-5-5-high"
    " | review-implementer composer-2.5\n"
)


def is_announced_fallback(entry):
    """An entry is an announced fallback when the ledger names a rejected slug."""
    return entry.rejected_slug is not None


def ledger_summary(parsed):
    """Reduce parsed ledger entries to {role: (slug, rejected_slug)} for whole-mapping asserts."""
    return {role: (entry.slug, entry.rejected_slug) for role, entry in parsed.items()}


class RosterTiersTestCase(unittest.TestCase):
    """Writes the three roster tiers into a temporary directory."""

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self.repo_path = root / "repo" / ".supercook" / "models.md"
        self.home_path = root / "home" / ".supercook" / "models.md"
        self.shipped_path = root / "plugin" / "skills" / "supercook" / "models.md"
        self.write(self.shipped_path, SHIPPED_FIXTURE)

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def load(self, repo_path="default"):
        if repo_path == "default":
            repo_path = self.repo_path
        return roster.load_roster(repo_path, self.home_path, self.shipped_path)


class RosterPrecedenceTests(RosterTiersTestCase):
    def test_each_role_takes_the_highest_tier_that_names_it(self):
        self.write(self.home_path, models_file("arena-a: home-arena-a", "arena-b: home-arena-b"))
        self.write(self.repo_path, models_file("arena-a: repo-arena-a"))

        expected = dict(SHIPPED_FIXTURE_ROSTER, **{"arena-a": "repo-arena-a", "arena-b": "home-arena-b"})
        self.assertEqual(self.load(), expected)

    def test_an_override_file_naming_one_role_changes_exactly_that_role(self):
        for tier, path in (("repository", self.repo_path), ("system", self.home_path)):
            with self.subTest(tier=tier):
                self.write(path, models_file("explorer: override-explorer"))
                try:
                    self.assertEqual(self.load(), dict(SHIPPED_FIXTURE_ROSTER, explorer="override-explorer"))
                finally:
                    path.unlink()

    def test_inherit_survives_as_a_value_at_every_tier(self):
        self.write(self.shipped_path, models_file("standard: inherit", "arena-a: shipped-a", "explorer: shipped-e"))
        self.write(self.home_path, models_file("arena-a: home-a", "explorer:   inherit   # session model"))
        self.write(self.repo_path, models_file("arena-a: inherit"))

        self.assertEqual(self.load(), {"standard": "inherit", "arena-a": "inherit", "explorer": "inherit"})


class MissingOverrideFileTests(RosterTiersTestCase):
    def test_missing_repository_file_or_no_repository_falls_through_to_system_then_shipped(self):
        self.write(self.home_path, models_file("arena-a: home-arena-a"))
        expected = dict(SHIPPED_FIXTURE_ROSTER, **{"arena-a": "home-arena-a"})


        for repo_path in (self.repo_path, None):
            with self.subTest(repo_path=repo_path):
                self.assertEqual(self.load(repo_path=repo_path), expected)

    def test_missing_repository_and_system_files_yield_the_shipped_roster(self):
        for repo_path in (self.repo_path, None):
            with self.subTest(repo_path=repo_path):
                self.assertEqual(self.load(repo_path=repo_path), SHIPPED_FIXTURE_ROSTER)

    def test_override_file_without_a_roster_block_leaves_lower_tiers_in_charge(self):
        self.write(self.repo_path, "# My notes\n\narena-a: repo-arena-a\n")

        self.assertEqual(self.load(), SHIPPED_FIXTURE_ROSTER)


class RosterLineGrammarTests(unittest.TestCase):
    def test_comments_are_stripped_and_spacing_after_the_colon_is_tolerated(self):
        parsed = roster.parse_roster(
            models_file(
                "standard:claude-opus-5-5-high",
                "arena-a:   inherit   # session model is the third family",
                "plan-optimizer: claude-opus-5-5-high",
                "implementer:\tgrok-4.7-high   ",
                "reviewer:      claude-opus-5-5-high   # bugbot, security-review",
            )
        )

        self.assertEqual(
            parsed,
            {
                "standard": "claude-opus-5-5-high",
                "arena-a": "inherit",
                "plan-optimizer": "claude-opus-5-5-high",
                "implementer": "grok-4.7-high",
                "reviewer": "claude-opus-5-5-high",
            },
        )

    def test_colon_lines_outside_the_roster_block_are_ignored(self):
        preamble = (
            "```bash\n"
            "curl -fsSL https://example.com/models.md -o ~/.supercook/models.md\n"
            "```\n\n"
            "Note: this line is prose, not a role.\n"
        )
        parsed = roster.parse_roster(models_file("explorer: composer-2.5", preamble=preamble))

        self.assertEqual(parsed, {"explorer": "composer-2.5"})

    def test_text_without_a_roster_section_yields_nothing(self):
        for text in ("# Model preferences\n\nNo roster here.\n", ""):
            with self.subTest(text=text):
                self.assertEqual(roster.parse_roster(text), {})

    def test_a_roster_body_with_crlf_newlines_returns_the_same_roles_as_lf(self):
        lf = models_file("standard: claude-opus-5-5-high", "explorer: composer-2.5")
        expected = {"standard": "claude-opus-5-5-high", "explorer": "composer-2.5"}

        self.assertEqual(roster.parse_roster(lf), expected)
        self.assertEqual(roster.parse_roster(lf.replace("\n", "\r\n")), expected)

    def test_a_roster_fence_opened_as_text_returns_the_roles_inside(self):
        body = models_file("arena-b: gpt-5.6-sol-max", "reviewer: claude-opus-5-5-high")
        labeled = body.replace("```\n", "```text\n", 1)

        self.assertEqual(
            roster.parse_roster(labeled),
            {"arena-b": "gpt-5.6-sol-max", "reviewer": "claude-opus-5-5-high"},
        )

    def test_shipped_models_file_defines_every_roster_role(self):
        parsed = roster.parse_roster(SHIPPED_MODELS_PATH.read_text(encoding="utf-8"))

        self.assertEqual(set(parsed), ROSTER_KEYS)
        self.assertEqual(parsed["arena-b"], "composer-2.5")
        self.assertEqual(parsed["standard"], "grok-4.7-high")


class LedgerModelsHeaderTests(unittest.TestCase):
    def test_each_header_entry_form_is_read_with_its_fallback_status(self):
        cases = [
            ("arena-b inherit (unavailable gpt-5.6-sol-max)", "arena-b", ("inherit", "gpt-5.6-sol-max"), True),
            ("explorer composer-2.5", "explorer", ("composer-2.5", None), False),
            ("arena-a inherit", "arena-a", ("inherit", None), False),
        ]
        for entry_text, role, expected, fallback in cases:
            with self.subTest(entry=entry_text):
                parsed = roster.parse_ledger_models(f"# Ledger\nrun-id: x\nmodels: {entry_text}\nui-change: no\n")

                self.assertEqual(ledger_summary(parsed), {role: expected})
                self.assertIs(is_announced_fallback(parsed[role]), fallback)

    def test_this_runs_own_ledger_header_marks_only_arena_b_as_fallback(self):
        parsed = roster.parse_ledger_models(THIS_RUN_MODELS_HEADER)

        self.assertEqual(set(parsed), ROSTER_KEYS)
        fallbacks = {role for role, entry in parsed.items() if is_announced_fallback(entry)}
        self.assertEqual(fallbacks, {"arena-b"})
        self.assertEqual(ledger_summary(parsed)["explorer"], ("composer-2.5", None))


class MalformedLedgerTests(unittest.TestCase):
    def test_ledger_without_a_models_header_yields_no_entries(self):
        cases = {
            "no models line": "# Ledger\nrun-id: x\n## Log\n",
            "empty text": "",
            "models word inside the log": "# Ledger\n## Log\n- 19:46 model fallback: models: arena-b inherit (unavailable x)\n",
        }
        for name, text in cases.items():
            with self.subTest(name):
                self.assertEqual(roster.parse_ledger_models(text), {})

    def test_malformed_entries_yield_a_partial_result_without_fallbacks(self):
        cases = {
            "old style header": ("models: shipped defaults ok | explorer inherit\n", "explorer", "inherit"),
            "truncated fallback": (
                "models: arena-b inherit (unavailable | explorer composer-2.5 | | garbage\n",
                "explorer",
                "composer-2.5",
            ),
        }
        for name, (text, valid_role, valid_slug) in cases.items():
            with self.subTest(name):
                parsed = roster.parse_ledger_models(text)

                self.assertEqual(parsed[valid_role].slug, valid_slug)
                self.assertFalse(any(is_announced_fallback(entry) for entry in parsed.values()))


if __name__ == "__main__":
    unittest.main()
