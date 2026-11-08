"""User-journey tests for roster and ledger parsing (hooks/roster.py).

Run with: python3 -m unittest discover hooks
"""

import tempfile
import unittest
from pathlib import Path

import roster

SHIPPED_MODELS_PATH = Path(__file__).resolve().parent.parent / "skills/supercook/models.md"

ROSTER_KEYS = {
    "standard",
    "arena-a",
    "arena-b",
    "arena-c",
    "plan-judge",
    "plan-optimizer",
    "implementer",
    "explorer",
    "reviewer",
    "review-implementer",
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


def is_announced_fallback(entry):
    """An entry is an announced fallback when the ledger names a rejected slug."""
    return entry.rejected_slug is not None


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


class ThreeTierPrecedenceTests(RosterTiersTestCase):
    def test_role_set_in_all_three_files_takes_the_repository_value(self):
        self.write(self.home_path, models_file("arena-a: home-arena-a"))
        self.write(self.repo_path, models_file("arena-a: repo-arena-a"))

        self.assertEqual(self.load()["arena-a"], "repo-arena-a")

    def test_role_set_only_in_system_and_shipped_files_takes_the_system_value(self):
        self.write(self.home_path, models_file("arena-b: home-arena-b"))
        self.write(self.repo_path, models_file("arena-a: repo-arena-a"))

        self.assertEqual(self.load()["arena-b"], "home-arena-b")

    def test_role_named_nowhere_above_shipped_keeps_the_shipped_value(self):
        self.write(self.home_path, models_file("arena-b: home-arena-b"))
        self.write(self.repo_path, models_file("arena-a: repo-arena-a"))

        self.assertEqual(self.load()["explorer"], "shipped-explorer")


class SingleRoleOverrideTests(RosterTiersTestCase):
    def test_repository_file_naming_one_role_changes_exactly_that_role(self):
        self.write(self.repo_path, models_file("explorer: repo-explorer"))
        expected = dict(SHIPPED_FIXTURE_ROSTER, explorer="repo-explorer")

        self.assertEqual(self.load(), expected)

    def test_system_file_naming_one_role_changes_exactly_that_role(self):
        self.write(self.home_path, models_file("reviewer: home-reviewer"))
        expected = dict(SHIPPED_FIXTURE_ROSTER, reviewer="home-reviewer")

        self.assertEqual(self.load(), expected)


class InheritValueTests(RosterTiersTestCase):
    def test_repository_inherit_beats_a_real_slug_below_it(self):
        self.write(self.home_path, models_file("arena-a: home-arena-a"))
        self.write(self.repo_path, models_file("arena-a: inherit"))

        self.assertEqual(self.load()["arena-a"], "inherit")

    def test_system_inherit_beats_the_shipped_slug(self):
        self.write(self.home_path, models_file("explorer:   inherit   # back to the session model"))

        self.assertEqual(self.load()["explorer"], "inherit")

    def test_shipped_inherit_survives_when_no_override_names_the_role(self):
        self.write(self.shipped_path, models_file("standard: inherit", "explorer: shipped-explorer"))

        self.assertEqual(self.load()["standard"], "inherit")


class MissingOverrideFileTests(RosterTiersTestCase):
    def test_missing_repository_file_falls_through_to_system_then_shipped(self):
        self.write(self.home_path, models_file("arena-a: home-arena-a"))
        result = self.load()

        self.assertEqual(result["arena-a"], "home-arena-a")
        self.assertEqual(result["arena-b"], "shipped-arena-b")

    def test_no_repository_root_falls_through_to_system_then_shipped(self):
        self.write(self.home_path, models_file("arena-a: home-arena-a"))
        result = self.load(repo_path=None)

        self.assertEqual(result["arena-a"], "home-arena-a")
        self.assertEqual(result["arena-b"], "shipped-arena-b")

    def test_missing_repository_and_system_files_yield_the_shipped_roster(self):
        self.assertEqual(self.load(), SHIPPED_FIXTURE_ROSTER)
        self.assertEqual(self.load(repo_path=None), SHIPPED_FIXTURE_ROSTER)

    def test_override_file_without_a_roster_block_leaves_lower_tiers_in_charge(self):
        self.write(self.repo_path, "# My notes\n\narena-a: repo-arena-a\n")

        self.assertEqual(self.load()["arena-a"], "shipped-arena-a")


class RosterLineGrammarTests(unittest.TestCase):
    def test_trailing_comment_yields_the_bare_slug(self):
        parsed = roster.parse_roster(models_file("reviewer: claude-opus-5-5-high   # bugbot, security-review"))

        self.assertEqual(parsed, {"reviewer": "claude-opus-5-5-high"})

    def test_variable_spacing_after_the_colon_is_tolerated(self):
        parsed = roster.parse_roster(
            models_file(
                "standard:claude-opus-5-5-high",
                "arena-a:      claude-fable-5-1-thinking-high",
                "plan-optimizer: claude-opus-5-5-high",
                "implementer:\tcursor-grok-4.6-xhigh-fast   ",
            )
        )

        self.assertEqual(
            parsed,
            {
                "standard": "claude-opus-5-5-high",
                "arena-a": "claude-fable-5-1-thinking-high",
                "plan-optimizer": "claude-opus-5-5-high",
                "implementer": "cursor-grok-4.6-xhigh-fast",
            },
        )

    def test_inherit_with_a_comment_stays_inherit(self):
        parsed = roster.parse_roster(models_file("arena-a:   inherit   # session model is the third family"))

        self.assertEqual(parsed, {"arena-a": "inherit"})

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
        self.assertEqual(roster.parse_roster("# Model preferences\n\nNo roster here.\n"), {})
        self.assertEqual(roster.parse_roster(""), {})


class ShippedModelsFileTests(unittest.TestCase):
    def test_shipped_models_file_defines_every_roster_role(self):
        parsed = roster.parse_roster(SHIPPED_MODELS_PATH.read_text(encoding="utf-8"))

        self.assertEqual(set(parsed), ROSTER_KEYS)
        self.assertEqual(parsed["arena-b"], "gpt-5.6-sol-max")
        self.assertEqual(parsed["standard"], "claude-opus-5-5-high")


class LedgerModelsHeaderTests(unittest.TestCase):
    HEADER = (
        "# Ledger: example run\n"
        "run-id: 2026-11-07-example\n"
        "models: standard claude-opus-5-5-high | arena-b inherit (unavailable gpt-5.6-sol-max)"
        " | explorer composer-2.5 | arena-a inherit\n"
        "ui-change: no\n"
    )

    def test_unavailable_role_is_read_as_an_announced_fallback(self):
        entry = roster.parse_ledger_models(self.HEADER)["arena-b"]

        self.assertTrue(is_announced_fallback(entry))
        self.assertEqual(entry.slug, "inherit")
        self.assertEqual(entry.rejected_slug, "gpt-5.6-sol-max")

    def test_normally_resolved_role_is_not_a_fallback(self):
        entry = roster.parse_ledger_models(self.HEADER)["explorer"]

        self.assertFalse(is_announced_fallback(entry))
        self.assertEqual(entry.slug, "composer-2.5")

    def test_plain_inherit_without_a_rejected_slug_is_not_a_fallback(self):
        entry = roster.parse_ledger_models(self.HEADER)["arena-a"]

        self.assertFalse(is_announced_fallback(entry))
        self.assertEqual(entry.slug, "inherit")

    def test_this_runs_own_ledger_header_marks_only_arena_b_as_fallback(self):
        ledger_text = (
            "models: standard claude-opus-5-5-high | arena-a claude-fable-5-1-thinking-high"
            " | arena-b inherit (unavailable gpt-5.6-sol-max) | arena-c claude-opus-5-5-high"
            " | plan-judge claude-opus-5-5-high | plan-optimizer claude-opus-5-5-high"
            " | implementer composer-2.5 | explorer composer-2.5 | reviewer claude-opus-5-5-high"
            " | review-implementer composer-2.5\n"
        )
        parsed = roster.parse_ledger_models(ledger_text)

        self.assertEqual(set(parsed), ROSTER_KEYS)
        fallbacks = {role for role, entry in parsed.items() if is_announced_fallback(entry)}
        self.assertEqual(fallbacks, {"arena-b"})


class MalformedLedgerTests(unittest.TestCase):
    def test_ledger_without_a_models_line_yields_no_entries(self):
        self.assertEqual(roster.parse_ledger_models("# Ledger\nrun-id: x\n## Log\n"), {})
        self.assertEqual(roster.parse_ledger_models(""), {})

    def test_old_style_header_yields_a_partial_result_without_fallbacks(self):
        parsed = roster.parse_ledger_models("models: shipped defaults ok | explorer inherit\n")

        self.assertEqual(parsed["explorer"].slug, "inherit")
        self.assertFalse(any(is_announced_fallback(entry) for entry in parsed.values()))

    def test_truncated_fallback_entry_is_not_an_announced_fallback(self):
        parsed = roster.parse_ledger_models(
            "models: arena-b inherit (unavailable | explorer composer-2.5 | | garbage\n"
        )

        self.assertEqual(parsed["explorer"].slug, "composer-2.5")
        self.assertFalse(any(is_announced_fallback(entry) for entry in parsed.values()))

    def test_models_word_inside_the_log_is_not_read_as_the_header(self):
        ledger_text = "# Ledger\n## Log\n- 19:46 model fallback: models: arena-b inherit (unavailable x)\n"

        self.assertEqual(roster.parse_ledger_models(ledger_text), {})


if __name__ == "__main__":
    unittest.main()
