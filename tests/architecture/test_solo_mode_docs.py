"""Guards the solo-mode intake gate. Run with: python3 -m unittest discover -s tests/architecture

Solo mode once started at Assess, so a parent could run every role without ever
creating .supercook/<run-id>/. These tests pin the phase 0 start, the two blocking
gates, the no-commit misread fix, and the trivial-only task-text verify contract.
"""

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

KICKOFF_DOC = "skills/supercook/references/coordinator-kickoff.md"
VERIFICATION_DOC = "skills/supercook/pipeline/verification.md"
VERIFIER_AGENT = "agents/supercook-verifier.md"
SOLO_HEADING = "### No spawn tool: run roles inline"


def solo_section() -> str:
    agents = read_doc(AGENTS_DOC)
    start = agents.index(SOLO_HEADING)
    return agents[start : agents.index("### Forbidden skips", start)]


def solo_step(number: int) -> str:
    """Return the text of one numbered solo step, up to the next numbered step."""
    section = solo_section()
    start = section.index(f"\n{number}. **")
    following = section.find(f"\n{number + 1}. **", start)
    return section[start:] if following == -1 else section[start:following]


class SoloGateTests(unittest.TestCase):
    def test_launch_rule_path_three_starts_at_phase_zero(self):
        rule = section_body(read_doc(SKILL_DOC), LAUNCH_RULE_HEADING)
        path_three = next(line for line in rule.splitlines() if line.startswith("3. **Solo mode.**"))
        for phrase in ("phase 0", "ledger.md", "assess row", "before any product file"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, path_three)

    def test_solo_list_starts_at_intake_and_follows_pipeline_phases(self):
        titles = ["Intake", "Assess", "Recon", "Design doc", "Plan", "Test-first", "Implement", "Verify", "Deliver"]
        for number, title in enumerate(titles):
            with self.subTest(step=number):
                self.assertIn(f"\n{number}. **{title}", solo_section())

    def test_intake_step_is_blocking_and_names_the_run_folder(self):
        step = solo_step(0)
        for phrase in ("`.supercook/<run-id>/`", "info/exclude", "`spawn: none`", "does not skip this step"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, step)

    def test_no_product_edit_until_assess_row_is_closed(self):
        step = solo_step(1)
        self.assertIn("**Gate:** no product file is created or changed until `ledger.md` exists", step)
        self.assertIn("closed `inline`", step)

    def test_no_test_commit_until_plan_md_exists(self):
        step = solo_step(4)
        self.assertIn("**Gate:** no test file is written or committed until `plan.md` exists", step)
        self.assertIn("spec pointer", step)

    def test_plan_step_precedes_test_step(self):
        section = solo_section()
        self.assertLess(section.index("\n4. **Plan"), section.index("\n5. **Test-first"))

    def test_deliver_step_says_no_independent_review(self):
        step = solo_step(8)
        self.assertIn("no independent review", step)
        self.assertIn("pre-PR check", step)


class NoCommitMisreadTests(unittest.TestCase):
    def test_intake_says_a_no_commit_rule_does_not_skip_the_run_folder(self):
        seeded = section_body(read_doc(INTAKE_DOC), "## 4. Seed the ledger")
        self.assertIn("does not skip this step", seeded)
        self.assertIn("logs, transcripts, or probe notes", seeded)
        self.assertIn("`keep ledger`", seeded)

    def test_ledger_lists_findings_in_pr_only_as_an_invalid_skip(self):
        ledger = read_doc(LEDGER_DOC)
        self.assertIn("`no artifacts in repo` / `findings in PR only` / `throwaway experiment`", ledger)

    def test_kickoff_says_solo_is_not_a_one_pass_implement(self):
        kickoff = read_doc(KICKOFF_DOC)
        self.assertIn("Solo is the same pipeline run by one agent, not a one-pass implement", kickoff)


class VerifierPlanContractTests(unittest.TestCase):
    def test_task_text_contract_is_trivial_only(self):
        docs = {
            "verification.md": read_doc(VERIFICATION_DOC),
            "agents.md": read_doc(AGENTS_DOC),
            "supercook-verifier.md": read_doc(VERIFIER_AGENT),
        }
        for name, text in docs.items():
            with self.subTest(doc=name):
                self.assertIn("Only a ledger `tier: trivial` has no `plan.md`", text)
                self.assertIn("`verdict: gaps found`", text)
                self.assertNotIn("A trivial run has no `plan.md`", text)


if __name__ == "__main__":
    unittest.main()
