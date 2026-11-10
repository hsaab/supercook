"""Guards the wording that keeps a /supercook parent coordinating instead of implementing.

Run with: python3 -m unittest discover -s tests/architecture

Cloud Agents were loading the skill, reading intake, and then doing the roster phases themselves.
These checks pin the pieces that stop that: the launch rule sits at the top of SKILL.md, every
roster phase names its worker, intake ends on a launch, and the ledger only closes a roster row
on a launch record.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills" / "supercook"

START_HERE_HEADING = "## Start here: you coordinate, workers do the phases"
LAUNCH_PATHS_IN_ORDER = ("1. **Typed.**", "2. **Any listed spawn tool.**", "3. **None.**")
WORKERS_BY_PHASE = {
    "1": ("supercook-assessor",),
    "2": ("supercook-explorer",),
    "4": (
        "supercook-planner",
        "supercook-arena-runner",
        "supercook-plan-judge",
        "supercook-plan-optimizer",
    ),
    "5": ("supercook-test-designer",),
    "6": ("supercook-implementer",),
    "7": ("supercook-verifier",),
}
TOOL_LISTING_PLACES = ("tool list", "dynamic tool catalog", "subagent types")
DELEGATION_PHRASE = "In a /supercook run, always use this"


def read_skill_doc(relative_path: str) -> str:
    return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")


def section_body(text: str, heading: str) -> str:
    """Return the text between a level-two heading and the next level-two heading."""
    start = text.index(heading) + len(heading)
    next_heading = re.search(r"^## ", text[start:], flags=re.MULTILINE)
    return text[start:] if next_heading is None else text[start : start + next_heading.start()]


def pipeline_rows(skill_text: str) -> dict[str, str]:
    """Map a pipeline phase number to its table row in SKILL.md."""
    rows = {}
    for line in section_body(skill_text, "## The pipeline").splitlines():
        match = re.match(r"^\| (\d) \|", line)
        if match:
            rows[match.group(1)] = line
    return rows


class SkillLaunchGateTest(unittest.TestCase):
    def setUp(self):
        self.skill = read_skill_doc("SKILL.md")

    def test_launch_rule_comes_before_the_first_principle(self):
        self.assertIn(START_HERE_HEADING, self.skill)
        self.assertLess(self.skill.index(START_HERE_HEADING), self.skill.index("## Principle 1"))

    def test_launch_rule_lists_the_three_paths_in_order(self):
        start_here = section_body(self.skill, START_HERE_HEADING)
        positions = [start_here.index(path) for path in LAUNCH_PATHS_IN_ORDER]
        self.assertEqual(positions, sorted(positions))

    def test_launch_rule_says_where_a_session_lists_its_tools(self):
        start_here = section_body(self.skill, START_HERE_HEADING)
        for place in TOOL_LISTING_PLACES:
            with self.subTest(place=place):
                self.assertIn(place, start_here)

    def test_launch_rule_keeps_the_tier_with_the_assessor(self):
        start_here = section_body(self.skill, START_HERE_HEADING)
        self.assertIn("first action after intake is the `supercook-assessor` launch", start_here)
        self.assertIn("faster or more efficient", start_here)

    def test_pipeline_table_names_the_worker_for_every_roster_phase(self):
        rows = pipeline_rows(self.skill)
        self.assertIn("| # | Phase | Run by | Guide |", self.skill)
        for phase, workers in WORKERS_BY_PHASE.items():
            for worker in workers:
                with self.subTest(phase=phase, worker=worker):
                    self.assertIn(f"`{worker}`", rows[phase])


class IntakeHandOffTest(unittest.TestCase):
    def setUp(self):
        self.intake = read_skill_doc("pipeline/intake.md")

    def test_intake_ends_on_a_launch(self):
        self.assertIn("## 5. Launch the first worker", self.intake)
        hand_off = section_body(self.intake, "## 5. Launch the first worker")
        self.assertIn("`supercook-assessor`", hand_off)

    def test_spawn_probe_names_every_place_tools_are_listed(self):
        for place in TOOL_LISTING_PLACES:
            with self.subTest(place=place):
                self.assertIn(place, self.intake)
        self.assertIn("spawn none (checked tool list, dynamic tool catalog, subagent types)", self.intake)


class LedgerAndContractTest(unittest.TestCase):
    def test_ledger_closes_roster_rows_only_on_a_launch_record(self):
        ledger = read_skill_doc("pipeline/ledger.md")
        self.assertIn("**A roster row closes on a launch record.**", ledger)
        self.assertIn("`faster inline` / `small task`", ledger)

    def test_forbidden_skips_cover_speed_and_size(self):
        agents_doc = read_skill_doc("agents.md")
        forbidden = agents_doc[agents_doc.index("### Forbidden skips") :]
        self.assertIn("`skip: faster inline`", forbidden)
        self.assertIn("`skip: small task`", forbidden)

    def test_agents_doc_says_where_agent_files_live_for_a_mirrored_skill(self):
        agents_doc = read_skill_doc("agents.md")
        self.assertIn("~/.cursor/plugins/local/supercook/agents/", agents_doc)


class PackagingDocsTest(unittest.TestCase):
    def test_every_agent_description_tells_cursor_when_to_delegate(self):
        for agent_file in sorted((REPO_ROOT / "agents").glob("supercook-*.md")):
            frontmatter = agent_file.read_text(encoding="utf-8").split("---")[1]
            description = next(
                line for line in frontmatter.splitlines() if line.startswith("description:")
            )
            with self.subTest(agent=agent_file.name):
                self.assertIn(DELEGATION_PHRASE, description)
                self.assertNotIn(": ", description.removeprefix("description: "))

    def test_readme_does_not_install_through_a_symlink(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("ln -s", readme)
        self.assertIn("### On Cloud Agents", readme)


if __name__ == "__main__":
    unittest.main()
