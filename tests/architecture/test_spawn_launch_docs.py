"""Guards the launch docs. Run with: python3 -m unittest discover -s tests/architecture

Two rules are pinned here, because both were broken by wording drift before:

1. Coordinators launch named supercook-<role> subagents through whatever spawn tool their session lists,
   so no launch doc may name a single host tool (such as task_v2) as the required path.
2. Whenever a session has a spawn path, every roster phase that runs is a launch. The rule has to open
   SKILL.md (the only file a /supercook invocation is certain to load), carry no tier exception, be
   echoed where a run reads next (intake, the ledger, the agent descriptions), and tell the parent
   where a session can list its spawn tool.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README_DOC = "README.md"
SKILL_DOC = "skills/supercook/SKILL.md"
AGENTS_DOC = "skills/supercook/agents.md"
INTAKE_DOC = "skills/supercook/pipeline/intake.md"
LEDGER_DOC = "skills/supercook/pipeline/ledger.md"
RECON_DOC = "skills/supercook/pipeline/recon.md"
INVESTIGATION_DOC = "skills/supercook/playbooks/investigation.md"
# Recorded before the first inline role when the session has no spawn tool.
CHECKED_SPAWN_NONE = "spawn none (checked tool list, dynamic tool catalog, subagent types)"
# Markdown target only. Plain text of this path may stay so a full checkout can still find it.
OUTSIDE_SKILL_LAUNCH_LINK = re.compile(
    r"\[[^\]]*\]\([^)]*\.cursor/supercook/subagent-launch\.md[^)]*\)"
)
LAUNCH_DOCS = (
    README_DOC,
    SKILL_DOC,
    AGENTS_DOC,
    INTAKE_DOC,
    LEDGER_DOC,
    "skills/supercook/references/coordinator-kickoff.md",
    ".cursor/rules/supercook-subagent-launch.mdc",
    ".cursor/supercook/subagent-launch.md",
)
PINNED_TOOL_NAMES = ("task_v2",)

# The Agent Skills standard caps a description at 1024 characters.
MAX_DESCRIPTION_CHARS = 1024
# Inside an unquoted YAML value these sequences end the value or start a comment,
# and a skill or agent whose frontmatter does not parse is dropped by the host.
YAML_PLAIN_SCALAR_BREAKERS = (": ", " #")

LAUNCH_RULE_HEADING = "## Start here: the launch rule"
INTAKE_LAUNCH_HEADING = "## 5. Launch the first worker"
LAUNCH_PATHS_IN_ORDER = ("1. **Typed.**", "2. **Any listed spawn tool.**", "3. **None.**")
# A Cloud Agent can list its spawn tool only inside a dynamic catalog, so the probe names every place.
TOOL_LISTING_PLACES = ("tool list", "dynamic tool catalog", "subagent types")
# Which named worker each roster phase launches, keyed by the pipeline table's phase number.
WORKERS_BY_PHASE = {
    "1": ("supercook-assessor",),
    "2": ("supercook-explorer",),
    "4": ("supercook-planner", "supercook-arena-runner", "supercook-plan-judge", "supercook-plan-optimizer"),
    "5": ("supercook-test-designer",),
    "6": ("supercook-implementer",),
    "7": ("supercook-verifier",),
}
# Wording that let a coordinator with a spawn tool do roster work itself by calling the task small.
TIER_EXCEPTION_PHRASES = (
    "**never** the parent on standard or complex tier",
    "does not solo-implement on **standard** or **complex** tier",
    "parent direct (assessor trivial)",
)


def read_doc(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def agent_files() -> list[Path]:
    return sorted((REPO_ROOT / "agents").glob("supercook-*.md"))


def frontmatter_description(text: str) -> str:
    """Return the single-line `description:` value from a file's YAML frontmatter."""
    frontmatter = text.split("---")[1]
    match = re.search(r"^description: (.+)$", frontmatter, re.MULTILINE)
    if match is None:
        raise AssertionError("frontmatter has no single-line description")
    return match.group(1)


def section_body(text: str, heading: str) -> str:
    """Return the text between a level-two heading and the next level-two heading."""
    start = text.index(heading) + len(heading)
    next_heading = re.search(r"^## ", text[start:], flags=re.MULTILINE)
    return text[start:] if next_heading is None else text[start : start + next_heading.start()]


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


def pipeline_table_rows(skill_text: str) -> dict[str, str]:
    """Map each phase number in SKILL.md's pipeline table to the text of its row."""
    rows = {}
    for line in section_body(skill_text, "## The pipeline").splitlines():
        match = re.match(r"^\| (\d) \|", line)
        if match:
            rows[match.group(1)] = line
    return rows


class SpawnLaunchDocsTest(unittest.TestCase):
    def test_no_launch_doc_pins_a_host_specific_spawn_tool(self):
        for relative_path in LAUNCH_DOCS:
            text = read_doc(relative_path)
            for tool_name in PINNED_TOOL_NAMES:
                with self.subTest(doc=relative_path, tool=tool_name):
                    self.assertNotIn(tool_name, text)

    def test_agents_doc_keeps_named_launch_and_inline_fallback(self):
        text = read_doc(AGENTS_DOC)
        self.assertIn("/supercook-<role>", text)
        self.assertIn("| `none` | No nested-spawn tool of any kind |", text)
        self.assertIn("### Forbidden skips", text)

    def test_every_agent_file_declares_its_supercook_name(self):
        self.assertEqual(len(agent_files()), 9)
        for agent_file in agent_files():
            with self.subTest(agent=agent_file.name):
                frontmatter = agent_file.read_text(encoding="utf-8").split("---")[1]
                self.assertIn(f"name: {agent_file.stem}", frontmatter)


class SkillLaunchRuleTest(unittest.TestCase):
    def setUp(self):
        self.skill = read_doc(SKILL_DOC)
        self.rule = section_body(self.skill, LAUNCH_RULE_HEADING)

    def test_launch_rule_comes_before_every_other_section(self):
        rule_position = self.skill.index(LAUNCH_RULE_HEADING)
        for later_heading in ("## Principle 1", "## The other principles", "## The pipeline"):
            with self.subTest(later_heading=later_heading):
                self.assertLess(rule_position, self.skill.index(later_heading))

    def test_launch_rule_lists_the_three_paths_in_order(self):
        positions = [self.rule.index(path) for path in LAUNCH_PATHS_IN_ORDER]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("`degraded: parent inline (spawn none)`", self.rule)

    def test_launch_rule_says_where_a_session_lists_its_tools(self):
        for place in TOOL_LISTING_PLACES:
            with self.subTest(place=place):
                self.assertIn(place, self.rule)
        self.assertIn("Never call, wait for, or invent a tool", self.rule)

    def test_launch_rule_covers_every_tier(self):
        self.assertIn("Every roster phase that runs is a launch", self.rule)
        self.assertIn("decide which phases run, never who runs them", self.rule)
        self.assertIn("first action after intake is the `supercook-assessor` launch", self.rule)
        self.assertIn("still a `supercook-implementer` launch and a `supercook-verifier` launch", self.rule)
        self.assertIn("faster or more efficient", self.rule)

    def test_pipeline_table_names_the_worker_for_every_roster_phase(self):
        rows = pipeline_table_rows(self.skill)
        self.assertIn("| # | Phase | Run by | Guide |", self.skill)
        for phase, workers in WORKERS_BY_PHASE.items():
            for worker in workers:
                with self.subTest(phase=phase, worker=worker):
                    self.assertIn(f"`{worker}`", rows[phase])

    def test_skill_description_names_the_coordinator_role(self):
        description = frontmatter_description(self.skill)
        self.assertIn("coordinates", description)
        self.assertIn("supercook-<role>", description)

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

    def test_launch_rule_records_checked_spawn_none_before_inline_work(self):
        """Path 3 records the checked spawn none line before the inline role and any product edit."""
        recorded = [
            paragraph
            for paragraph in paragraphs_containing(self.rule, CHECKED_SPAWN_NONE)
            if all(phrase in paragraph for phrase in ("before", "inline", "product"))
        ]
        self.assertTrue(
            recorded,
            "launch rule does not record the checked spawn none line before inline work",
        )


class LaunchRuleEchoTest(unittest.TestCase):
    """The rule has to be repeated in the files a run reads after SKILL.md."""

    def test_no_launch_doc_keeps_a_tier_exception_for_solo_work(self):
        for relative_path in LAUNCH_DOCS:
            text = read_doc(relative_path)
            for phrase in TIER_EXCEPTION_PHRASES:
                with self.subTest(doc=relative_path, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_intake_ends_on_a_launch(self):
        intake = read_doc(INTAKE_DOC)
        self.assertIn(INTAKE_LAUNCH_HEADING, intake)
        first_launch = section_body(intake, INTAKE_LAUNCH_HEADING)
        self.assertIn("`supercook-assessor`", first_launch)
        self.assertIn("`degraded: parent inline (spawn none)`", first_launch)

    def test_spawn_probe_names_every_place_tools_are_listed(self):
        intake = read_doc(INTAKE_DOC)
        for place in TOOL_LISTING_PLACES:
            with self.subTest(place=place):
                self.assertIn(place, intake)
        self.assertIn("spawn none (checked tool list, dynamic tool catalog, subagent types)", intake)

    def test_ledger_closes_roster_rows_only_on_a_launch_record(self):
        ledger = read_doc(LEDGER_DOC)
        self.assertIn("**A roster row closes on a launch record.**", ledger)
        self.assertIn("That holds at every tier, trivial included.", ledger)
        self.assertIn("`faster inline` / `small task`", ledger)

    def test_forbidden_skips_cover_speed_and_size(self):
        agents_doc = read_doc(AGENTS_DOC)
        forbidden = agents_doc[agents_doc.index("### Forbidden skips") :]
        for reason in ("`faster inline`", "`small task`"):
            with self.subTest(reason=reason):
                self.assertIn(reason, forbidden)

    def test_agents_doc_says_where_agent_files_live_for_a_mirrored_skill(self):
        agents_doc = read_doc(AGENTS_DOC)
        self.assertIn("~/.cursor/agents/", agents_doc)
        self.assertIn("~/.cursor/plugins/local/supercook/agents/", agents_doc)


class HandoffDecisionPointsTest(unittest.TestCase):
    """The same three decisions, echoed where a run reads after the launch rule."""

    def test_intake_records_spawn_none_before_the_inline_role(self):
        intake = read_doc(INTAKE_DOC)
        first_launch = section_body(intake, INTAKE_LAUNCH_HEADING)
        recorded = [
            paragraph
            for paragraph in paragraphs_containing(first_launch, CHECKED_SPAWN_NONE)
            if all(phrase in paragraph for phrase in ("before", "inline", "product"))
        ]
        self.assertTrue(
            recorded,
            "intake step 5 does not record the checked spawn none line before the inline role",
        )

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
        rule_6_start = rules.index("6. **A roster row closes on a launch record.**")
        rule_6_end = rules.index("\n### ", rule_6_start)
        rule_6 = rules[rule_6_start:rule_6_end]
        with self.subTest(place="agents spawn paragraph"):
            self.assertRegex(spawn_paragraph, r"\[[^\]]*\]\([^)]*SKILL\.md[^)]*\)")
            self.assertNotRegex(spawn_paragraph, OUTSIDE_SKILL_LAUNCH_LINK)
        with self.subTest(place="ledger rule 6"):
            self.assertRegex(rule_6, r"\[[^\]]*\]\([^)]*agents\.md[^)]*\)")
            self.assertNotRegex(rule_6, OUTSIDE_SKILL_LAUNCH_LINK)


class PackagingDocsTest(unittest.TestCase):
    def test_every_agent_description_says_when_it_must_be_used(self):
        for agent_file in agent_files():
            description = frontmatter_description(agent_file.read_text(encoding="utf-8"))
            with self.subTest(agent=agent_file.name):
                self.assertIn("Always use", description)
                self.assertIn("supercook run", description)

    def test_descriptions_stay_loadable_frontmatter(self):
        described_files = [REPO_ROOT / SKILL_DOC, *agent_files()]
        for described_file in described_files:
            description = frontmatter_description(described_file.read_text(encoding="utf-8"))
            with self.subTest(file=described_file.name):
                self.assertLessEqual(len(description), MAX_DESCRIPTION_CHARS)
                for breaker in YAML_PLAIN_SCALAR_BREAKERS:
                    self.assertNotIn(breaker, description)

    def test_readme_does_not_install_through_a_symlink(self):
        readme = read_doc(README_DOC)
        self.assertNotIn("ln -s", readme)
        self.assertIn("### On Cloud Agents", readme)


if __name__ == "__main__":
    unittest.main()
