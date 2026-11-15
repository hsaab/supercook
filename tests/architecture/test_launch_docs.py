"""Structural guards for the launch docs. Run with: python3 -m unittest discover -s tests/architecture

Earlier versions pinned launch wording sentence by sentence, and the launch rule grew
to five copies across six files while those tests stayed green. These tests check
structure instead: links and anchors resolve, every worker a doc names has an agent
file, the playbook steps carry their launches, and the launch section stays short.
"""

import json
import re
import unittest
from pathlib import Path

from doc_helpers import (
    ASSESS_DOC,
    LAUNCH_RULE_HEADING,
    README_DOC,
    REPO_ROOT,
    SKILL_DOC,
    agent_files,
    agent_names,
    frontmatter_description,
    playbook_files,
    read_doc,
    section_body,
    skill_docs,
    steps_block,
    strip_code_fences,
)

# The Agent Skills standard caps a description at 1024 characters.
MAX_DESCRIPTION_CHARS = 1024
# Inside an unquoted YAML value these sequences end the value or start a comment,
# and a skill or agent whose frontmatter does not parse is dropped by the host.
YAML_PLAIN_SCALAR_BREAKERS = (": ", " #")
# The launch rule regrew to 22 dense lines once; runs then skimmed past it.
MAX_LAUNCH_RULE_LINES = 16
LINK = re.compile(r"\]\(([^)\s]+)\)")
WORKER_NAME = re.compile(r"\bsupercook-[a-z]+(?:-[a-z]+)*\b")
# supercook-* tokens that name something other than a worker.
NOT_WORKERS = {"supercook-agents", "supercook-marketplace"}
TRACKS_THAT_CHANGE_CODE = ("feature", "bugfix", "refactor", "implement-plan")
SCRIPT_PATH = re.compile(r"\b((?:scripts|hooks)/[a-z_]+\.py)\b")


def heading_anchor(heading: str) -> str:
    """GitHub-style anchor for a markdown heading."""
    text = heading.strip().lower().replace("`", "")
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors_in(path: Path) -> set[str]:
    text = strip_code_fences(path.read_text(encoding="utf-8"))
    return {heading_anchor(match) for match in re.findall(r"^#{1,6} (.+)$", text, flags=re.MULTILINE)}


def docs_to_check() -> list[Path]:
    return [*skill_docs(), REPO_ROOT / README_DOC, *agent_files()]


class LinkIntegrityTest(unittest.TestCase):
    def test_every_relative_link_and_anchor_resolves(self):
        for doc in docs_to_check():
            text = strip_code_fences(doc.read_text(encoding="utf-8"))
            for target in LINK.findall(text):
                if re.match(r"^[a-z]+:", target):
                    continue
                file_part, _, anchor = target.partition("#")
                linked = (doc.parent / file_part).resolve() if file_part else doc
                with self.subTest(doc=doc.relative_to(REPO_ROOT).as_posix(), link=target):
                    self.assertTrue(linked.exists(), f"{target} points at a missing file")
                    if anchor and linked.suffix == ".md":
                        self.assertIn(anchor, anchors_in(linked), f"{target} points at a missing heading")

    def test_every_script_a_doc_names_exists(self):
        for doc in docs_to_check():
            for script in SCRIPT_PATH.findall(doc.read_text(encoding="utf-8")):
                with self.subTest(doc=doc.name, script=script):
                    self.assertTrue((REPO_ROOT / script).is_file(), f"{script} does not exist")


class WorkerNamesTest(unittest.TestCase):
    def test_every_worker_the_skill_names_has_an_agent_file(self):
        # intake.md names supercook-assessor on purpose, as the sign of an older install.
        known = agent_names() | NOT_WORKERS
        for doc in [*skill_docs(), REPO_ROOT / SKILL_DOC]:
            text = doc.read_text(encoding="utf-8")
            if doc.name == "intake.md":
                text = text.replace("`supercook-assessor`", "")
            for name in set(WORKER_NAME.findall(text)):
                with self.subTest(doc=doc.name, worker=name):
                    self.assertIn(name, known)

    def test_every_agent_file_is_named_in_the_pipeline_table(self):
        pipeline = section_body(read_doc(SKILL_DOC), "## The pipeline")
        for name in agent_names():
            with self.subTest(agent=name):
                self.assertIn(f"`{name}`", pipeline)

    def test_the_parent_runs_assess(self):
        pipeline = section_body(read_doc(SKILL_DOC), "## The pipeline")
        assess_row = next(line for line in pipeline.splitlines() if line.startswith("| 1 |"))
        self.assertIn("| You |", assess_row)
        self.assertIn("pipeline/assess.md", assess_row)
        self.assertTrue((REPO_ROOT / ASSESS_DOC).is_file())


class PlaybookStepsTest(unittest.TestCase):
    def test_tracks_that_change_code_launch_implementer_and_verifier_from_their_steps(self):
        for track in TRACKS_THAT_CHANGE_CODE:
            steps = steps_block(read_doc(f"skills/supercook/playbooks/{track}.md"))
            for worker in ("supercook-implementer", "supercook-verifier"):
                with self.subTest(track=track, worker=worker):
                    self.assertIn(worker, steps)

    def test_investigation_steps_launch_the_explorer(self):
        self.assertIn("supercook-explorer", steps_block(read_doc("skills/supercook/playbooks/investigation.md")))

    def test_every_playbook_has_a_steps_checklist(self):
        for playbook in playbook_files():
            with self.subTest(playbook=playbook.name):
                self.assertTrue(steps_block(playbook.read_text(encoding="utf-8")).strip())


class LaunchRuleTest(unittest.TestCase):
    def setUp(self):
        self.skill = read_doc(SKILL_DOC)
        self.rule = section_body(self.skill, LAUNCH_RULE_HEADING)

    def test_launch_rule_is_the_first_section(self):
        first_heading = re.search(r"^## (?!Contents).+$", self.skill, flags=re.MULTILINE).group(0)
        self.assertEqual(first_heading, LAUNCH_RULE_HEADING)

    def test_launch_rule_stays_short(self):
        lines = [line for line in self.rule.splitlines() if line.strip()]
        self.assertLessEqual(len(lines), MAX_LAUNCH_RULE_LINES)

    def test_launch_rule_names_the_launch_fields_and_both_fallbacks(self):
        for phrase in ("subagent_type: supercook-<role>", "generalPurpose", "agents/supercook-<role>.md",
                       "agents.md#no-spawn-tool-run-roles-inline", "run_in_background"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.rule)


class PackagingTest(unittest.TestCase):
    def test_every_agent_file_name_matches_its_frontmatter_name(self):
        for agent_file in agent_files():
            with self.subTest(agent=agent_file.name):
                self.assertIn(f"\nname: {agent_file.stem}\n", agent_file.read_text(encoding="utf-8"))

    def test_every_agent_description_says_when_it_must_be_used(self):
        for agent_file in agent_files():
            description = frontmatter_description(agent_file.read_text(encoding="utf-8"))
            with self.subTest(agent=agent_file.name):
                self.assertIn("Always use", description)
                self.assertIn("supercook run", description)

    def test_descriptions_stay_loadable_frontmatter(self):
        for described_file in [REPO_ROOT / SKILL_DOC, *agent_files()]:
            description = frontmatter_description(described_file.read_text(encoding="utf-8"))
            with self.subTest(file=described_file.name):
                self.assertLessEqual(len(description), MAX_DESCRIPTION_CHARS)
                for breaker in YAML_PLAIN_SCALAR_BREAKERS:
                    self.assertNotIn(breaker, description)

    def test_readme_counts_the_agents_that_ship(self):
        count_words = {7: "seven", 8: "eight", 9: "nine", 10: "ten"}
        self.assertIn(f"{count_words[len(agent_files())]} agents", read_doc(README_DOC))

    def test_plugin_manifest_ships_no_hooks_and_a_semver_version(self):
        manifest = json.loads(read_doc(".cursor-plugin/plugin.json"))
        self.assertNotIn("hooks", manifest)
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")

    def test_readme_does_not_install_through_a_symlink(self):
        readme = read_doc(README_DOC)
        self.assertNotIn("ln -s", readme)
        self.assertIn("### On Cloud Agents", readme)


if __name__ == "__main__":
    unittest.main()
