"""Guards the handoff decisions the launch rule echoes into later docs.

Run with: python3 -m unittest discover -s tests/architecture

After the assessor, the launch rule names the next worker, picks a spawn shape
from the tool schema, and relaunches a thin or wrong return. Intake, recon, and the investigation
playbook echo those same decisions.
"""

import re
import unittest

from test_spawn_launch_docs import (
    AGENTS_DOC,
    INTAKE_DOC,
    LAUNCH_RULE_HEADING,
    LEDGER_DOC,
    SKILL_DOC,
    read_doc,
    section_body,
)

RECON_DOC = "skills/supercook/pipeline/recon.md"
INVESTIGATION_DOC = "skills/supercook/playbooks/investigation.md"


def paragraphs_of(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def paragraphs_containing(text: str, phrase: str) -> list[str]:
    """Return every paragraph that holds phrase. Fail when none do."""
    matches = [paragraph for paragraph in paragraphs_of(text) if phrase in paragraph]
    if not matches:
        raise AssertionError(f"missing phrase: {phrase}")
    return matches


def sentences_of(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


class HandoffDocsTests(unittest.TestCase):
    """The launch rule's handoff decisions, and the same decisions echoed later."""

    def setUp(self):
        self.skill = read_doc(SKILL_DOC)
        self.rule = section_body(self.skill, LAUNCH_RULE_HEADING)

    def test_launch_rule_names_the_post_assessor_workers(self):
        """After the assessor, standard and complex launch explorer, and trivial launches implementer."""
        next_workers = [
            paragraph
            for paragraph in paragraphs_containing(self.rule, "supercook-explorer")
            if "supercook-implementer" in paragraph
        ]
        self.assertTrue(next_workers, "launch rule does not name the worker after the assessor")
        next_worker = next_workers[0]
        for phrase in ("assessor", "standard", "complex", "trivial"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, next_worker)

    def test_launch_rule_picks_the_spawn_shape_from_the_tool_schema(self):
        """Listed type, else custom plus a name, else general-purpose. Plan-optimizer takes the last."""
        rule_sentences = sentences_of(self.rule)
        listed = [
            sentence
            for sentence in rule_sentences
            if "listed type" in sentence and "path 1" in sentence
        ]
        custom_sentences = [
            sentence for sentence in rule_sentences if re.search(r"\bcustom\b", sentence)
        ]
        general = [sentence for sentence in rule_sentences if "general-purpose" in sentence]
        optimizer = [
            sentence for sentence in rule_sentences if "plan-optimizer" in sentence.casefold()
        ]
        with self.subTest(branch="listed type"):
            self.assertTrue(listed, "no sentence names a listed supercook-<role> type as path 1")
        with self.subTest(branch="free value and name"):
            self.assertTrue(
                custom_sentences,
                "no sentence sets type custom when the type field accepts a free value and a name field exists",
            )
            for sentence in custom_sentences:
                # custom is only that branch. A fixed list is not told to send it.
                self.assertIn("free value", sentence)
                self.assertIn("name field", sentence)
        with self.subTest(branch="general-purpose"):
            self.assertTrue(general, "no sentence uses the general-purpose type")
            for sentence in general:
                self.assertIn("supercook-<role>", sentence)
                self.assertIn("description", sentence)
                self.assertIn("agent", sentence)
                self.assertIn("prompt", sentence)
                self.assertNotRegex(sentence, r"\bcustom\b")
        with self.subTest(branch="plan-optimizer"):
            self.assertTrue(optimizer, "plan-optimizer is not named as today's last-branch role")
            for sentence in optimizer:
                self.assertNotRegex(sentence, r"\bcustom\b")

    def test_launch_rule_relaunches_a_thin_or_wrong_return(self):
        """A thin or wrong return is a fresh relaunch. That paragraph does not say resume."""
        relaunches = paragraphs_containing(self.rule, "relaunch")
        self.assertTrue(
            any(
                all(phrase in paragraph for phrase in ("fresh", "thin", "wrong", "rebuild"))
                for paragraph in relaunches
            ),
            "launch rule does not say to relaunch a thin or wrong return instead of rebuilding it",
        )
        for paragraph in relaunches:
            self.assertNotRegex(paragraph, r"\bresume\b")

    def test_intake_seeds_active_run(self):
        intake = read_doc(INTAKE_DOC)
        seeded = section_body(intake, "## 4. Seed the ledger")
        pointers = paragraphs_containing(seeded, ".supercook/active-run")
        self.assertTrue(
            any(
                all(phrase in paragraph for phrase in ("relative", "investigation", "does not", "deliver", "abandoned"))
                for paragraph in pointers
            ),
            "seeding a ledger does not write .supercook/active-run, or does not say investigation skips it",
        )

    def test_recon_names_supercook_explorer(self):
        recon = read_doc(RECON_DOC)
        opening, _separator, _rest = recon.partition("## Fan-out")
        fan_out = section_body(recon, "## Fan-out")
        with self.subTest(place="opening"):
            self.assertIn("supercook-explorer", opening)
        with self.subTest(place="fan-out"):
            self.assertIn("supercook-explorer", fan_out)

    def test_recon_relaunches_a_wrong_explorer_return(self):
        recon = read_doc(RECON_DOC)
        gap = section_body(recon, "## When recon is not enough")
        relaunches = paragraphs_containing(gap, "relaunch")
        self.assertTrue(
            any(
                all(phrase in paragraph for phrase in ("fresh", "wrong", "thin", "question", "explorer", "scan"))
                for paragraph in relaunches
            ),
            "recon does not say to relaunch a wrong or thin explorer return",
        )
        for paragraph in relaunches:
            self.assertNotRegex(paragraph, r"\bresume\b")

    def test_investigation_steps_name_supercook_explorer(self):
        playbook = read_doc(INVESTIGATION_DOC)
        steps = section_body(playbook, "## Steps")
        self.assertIn("explore with citations", steps)
        self.assertIn("supercook-explorer", steps)
        relaunches = paragraphs_containing(steps, "relaunch")
        self.assertTrue(
            any(all(phrase in paragraph for phrase in ("fresh", "thin", "wrong")) for paragraph in relaunches),
            "investigation steps do not say to relaunch a thin or wrong explorer return",
        )
        for paragraph in relaunches:
            self.assertNotRegex(paragraph, r"\bresume\b")

    def test_cited_skill_links_stay_inside_the_skill_tree(self):
        agents = read_doc(AGENTS_DOC)
        spawn_paragraph = paragraphs_containing(
            agents, "A spawn tool is not always in the top-level tool list."
        )[0]
        ledger = read_doc(LEDGER_DOC)
        rules = section_body(ledger, "## Rules")
        rule_6_start = rules.index("6. **A roster row closes on a launch record or an `inline` record.**")
        rule_6_end = rules.index("\n### ", rule_6_start)
        rule_6 = rules[rule_6_start:rule_6_end]
        with self.subTest(place="agents spawn paragraph"):
            self.assertRegex(spawn_paragraph, r"\[[^\]]*\]\([^)]*SKILL\.md[^)]*\)")
        with self.subTest(place="ledger rule 6"):
            self.assertRegex(rule_6, r"\[[^\]]*\]\([^)]*agents\.md[^)]*\)")


if __name__ == "__main__":
    unittest.main()
