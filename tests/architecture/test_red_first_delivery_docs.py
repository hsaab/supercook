"""Guards red-first stubs, acceptance criteria, and the fail-closed pre-PR check.

Run with: python3 -m unittest discover -s tests/architecture

Red tests used to be allowed to fail on "module not found", and the test designer
banned even a temporary stub. Delivery also had no durable proof on the PR. These
tests pin the stub procedure, the acceptance criteria chain, and the pre-PR check.
"""

import unittest

from test_spawn_launch_docs import AGENTS_DOC, INTAKE_DOC, read_doc, section_body

DELIVERY_DOC = "skills/supercook/pipeline/delivery.md"
IMPLEMENTATION_DOC = "skills/supercook/pipeline/implementation.md"
PLANNING_DOC = "skills/supercook/pipeline/planning.md"
VERIFICATION_DOC = "skills/supercook/pipeline/verification.md"
OPEN_PR_DOC = "skills/supercook/playbooks/open-pr.md"
README_DOC = "README.md"
TEST_DESIGNER = "agents/supercook-test-designer.md"
PLANNER = "agents/supercook-planner.md"
PLAN_JUDGE = "agents/supercook-plan-judge.md"
GAPS_SENTENCE = "A criterion no slice proves goes under Gaps, never silently dropped."
PLAN_WRITERS = (
    "agents/supercook-planner.md",
    "agents/supercook-plan-judge.md",
    "agents/supercook-plan-optimizer.md",
)


def between(text: str, start_heading: str, end_heading: str) -> str:
    """Return text from one heading to another. section_body stops at `## ` lines inside code fences."""
    start = text.index(start_heading)
    return text[start : text.index(end_heading, start)]


class RedFirstStubTests(unittest.TestCase):
    def setUp(self):
        self.designer = read_doc(TEST_DESIGNER)

    def test_test_designer_allows_only_a_temporary_stub(self):
        self.assertNotIn("not even the smallest stub", self.designer)
        self.assertIn("temporary stub", self.designer)
        self.assertIn("Never commit it", self.designer)

    def test_test_designer_example_is_an_assertion_failure(self):
        self.assertIn("fails because allowRequest returned true for the 101st request", self.designer)
        self.assertIn("not `fails because src/rate-limit/bucket.ts does not exist yet`", self.designer)

    def test_test_designer_returns_stub_and_red_evidence(self):
        returns = self.designer[self.designer.index("## Returns") :]
        self.assertIn("stub: <path, deleted | not needed>", returns)
        self.assertIn("red-evidence:", returns)

    def test_test_designer_returns_include_a_stub_patch_line(self):
        returns = self.designer[self.designer.index("## Returns") :]
        self.assertIn("stub-patch: <run-folder>/red-stub.patch | not needed", returns)

    def test_test_designer_guard_applies_stub_patch_on_a_journey_assertion(self):
        guards = section_body(read_doc(AGENTS_DOC), "## Parent-side guards")
        guard = next(line for line in guards.splitlines() if line.startswith("| `supercook-test-designer` |"))
        self.assertIn("When `stub-patch` names a patch, apply it", guard)
        self.assertIn("journey assertion", guard)
        self.assertIn("not a setup assertion", guard)

    def test_implementation_guide_runs_tests_against_an_uncommitted_stub(self):
        guide = section_body(read_doc(IMPLEMENTATION_DOC), "## Phase 5: test-first")
        for phrase in ("temporary stub", "never a committed one", "red-evidence", "tests only"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guide)

    def test_agents_contract_and_guard_cover_the_stub(self):
        agents = read_doc(AGENTS_DOC)
        self.assertIn("`stub` (`<path>, deleted` or `not needed`)", agents)
        self.assertIn("so no stub is left behind", agents)


class AcceptanceCriteriaTests(unittest.TestCase):
    def test_intake_pins_acceptance_criteria_verbatim(self):
        seeded = section_body(read_doc(INTAKE_DOC), "## 4. Seed the ledger")
        self.assertIn("`acceptance.md`", seeded)
        self.assertIn("verbatim", seeded)
        self.assertIn("`AC-1`", seeded)

    def test_plan_writers_map_every_criterion(self):
        for path in PLAN_WRITERS:
            with self.subTest(agent=path):
                self.assertIn("acceptance.md", read_doc(path))
        planning = section_body(read_doc(PLANNING_DOC), "## Acceptance criteria")
        self.assertIn("slice <n>, <named test or check>", planning)

    def test_plan_judge_sends_an_unproven_criterion_under_gaps(self):
        planner = between(read_doc(PLANNER), "## Acceptance criteria", "## Risks")
        judge = between(read_doc(PLAN_JUDGE), "## Acceptance criteria", "## Risks")
        self.assertIn(GAPS_SENTENCE, planner)
        self.assertIn(GAPS_SENTENCE, judge)

    def test_verifier_proves_each_criterion(self):
        verification = read_doc(VERIFICATION_DOC)
        self.assertIn("**Acceptance criteria**", verification)
        self.assertIn("An\n   unproven criterion is `gaps found`.", verification)
        self.assertIn("AC-1:", read_doc("agents/supercook-verifier.md"))


class EvidenceAndPreflightTests(unittest.TestCase):
    def setUp(self):
        self.delivery = read_doc(DELIVERY_DOC)

    def test_evidence_section_has_red_first_table_and_solo_line(self):
        evidence = between(self.delivery, "## Evidence section", "## UI delivery guard")
        for phrase in (
            "## Evidence",
            "Red first",
            "| Acceptance criterion (verbatim) | Test or check | Passing output |",
            "Built in solo mode, no independent review",
            "never in the diff",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, evidence)

    def test_pre_pr_check_fails_closed_on_four_conditions(self):
        check = section_body(self.delivery, "## Pre-PR check")
        self.assertIn("fails closed", check)
        self.assertIn("the PR is not opened", check)
        for phrase in (
            "**Every row is settled.**",
            "**The diff holds only scoped files.**",
            "**Every criterion has proof.**",
            "**The Evidence section is filled**",
        ):
            with self.subTest(condition=phrase):
                self.assertIn(phrase, check)

    def test_pre_pr_check_names_evidence_files_that_fail_it(self):
        check = section_body(self.delivery, "## Pre-PR check")
        for phrase in ("QA note", "log", "sweep output", "regen script", "leftover stub"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, check)

    def test_pre_pr_diff_item_counts_the_test_first_commit(self):
        check = section_body(self.delivery, "## Pre-PR check")
        item = next(line for line in check.splitlines() if line.startswith("2. "))
        self.assertIn("test-first commit of its slice", item)

    def test_pr_body_format_says_evidence_always_applies(self):
        intro = section_body(self.delivery, "## PR body format")
        self.assertIn("Evidence always applies.", intro)

    def test_open_pr_body_includes_the_evidence_heading(self):
        body = section_body(read_doc(OPEN_PR_DOC), "## The PR body")
        self.assertIn("`## Evidence`", body)

    def test_readme_no_longer_calls_hosted_bugbot_the_independent_review(self):
        readme = read_doc(README_DOC)
        self.assertNotIn("hosted Bugbot is the independent review", readme)
        self.assertIn("no independent review", readme)


if __name__ == "__main__":
    unittest.main()
