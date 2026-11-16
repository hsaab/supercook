"""Structural checks for the skill and agent docs. Run: python3 -m unittest discover -s tests

These check structure, not wording: links resolve, every named worker and file
exists, the playbook steps carry the worker launches the stop hook reads, the
frontmatter stays loadable, and the docs stay inside pstack-sized budgets.
"""

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / "skills" / "supercook"
SKILL_FILES = sorted((REPO / "skills").glob("*/SKILL.md"))
AGENTS_DIR = REPO / "agents"

sys.path.insert(0, str(REPO / "scripts"))
import run_folder  # noqa: E402

# Size budgets, in words, since each paragraph is one line. The skill regrew past 230
# lines and 18 phase docs once; these keep the always-read file and each playbook near
# pstack's proportions.
MAX_SKILL_WORDS = 1600
MAX_PLAYBOOK_WORDS = 450
MAX_REFERENCE_WORDS = 1100
MAX_AGENT_WORDS = 750
# The Agent Skills standard caps a description at 1024 characters, and inside an
# unquoted YAML value these sequences end the value or start a comment.
MAX_DESCRIPTION_CHARS = 1024
YAML_PLAIN_SCALAR_BREAKERS = (": ", " #")

LINK = re.compile(r"\]\(([^)\s]+)\)")
WORKER = re.compile(r"\bsupercook-[a-z]+(?:-[a-z]+)*\b")
NOT_WORKERS = {"supercook-marketplace", "supercook-delegation"}
# Removed agents may be named only as the sign of an older install, in these docs.
REMOVED_AGENTS = {"supercook-assessor", "supercook-plan-optimizer"}
OLDER_INSTALL_DOCS = (SKILL_DIR / "SKILL.md", REPO / "README.md")
SCRIPT = re.compile(r"\b((?:scripts|hooks)/[a-z_]+\.py)\b")
STEP_REFERENCE = re.compile(r"\breferences/[a-z-]+\.md\b")
TRACKS_THAT_CHANGE_CODE = ("feature", "bugfix", "refactor", "implement-plan")
ROSTER_CHOICES = ("roster:repo", "roster:local")
REPO_ROSTER = "<workspace-root>/.supercook/models.md"
HOME_ROSTER = "~/.supercook/models.md"
SHIPPED_ROSTER = "this file"
ROSTER_FILE = re.compile(r"`([^`]*models\.md)`|(this file)")
VERSION_LINE = re.compile(r"^supercook: (\S+) from \S+ \| roster: (\S+)$", re.MULTILINE)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_code_fences(text: str) -> str:
    return re.sub(r"^[ \t]*```.*?^[ \t]*```", "", text, flags=re.MULTILINE | re.DOTALL)


def anchors_in(path: Path) -> set[str]:
    headings = re.findall(r"^#{1,6} (.+)$", strip_code_fences(read(path)), flags=re.MULTILINE)
    return {re.sub(r"[^\w\- ]", "", h.strip().lower().replace("`", "")).replace(" ", "-") for h in headings}


def agent_files() -> list[Path]:
    return sorted(AGENTS_DIR.glob("supercook-*.md"))


def skill_docs() -> list[Path]:
    return sorted((REPO / "skills").rglob("*.md"))


def playbooks() -> list[Path]:
    return sorted((SKILL_DIR / "playbooks").glob("*.md"))


def checklist(playbook: Path) -> list[str]:
    """Every row of the fenced `## Steps` checklist, nested rows included."""
    steps = read(playbook).split("## Steps", 1)[1]
    block = re.search(r"^```\n(.*?)^```", steps, flags=re.MULTILINE | re.DOTALL)
    if block is None:
        raise AssertionError(f"{playbook.name}: ## Steps has no fenced checklist")
    return [line for line in block.group(1).splitlines() if line.lstrip().startswith("- [ ] ")]


def section(path: Path, heading: str) -> str:
    return read(path).split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def roster_choices() -> dict[str, tuple[str, list[str], str]]:
    """The roster table in models.md: choice -> (ask cell, files merged per role in order, ledger value)."""
    table = {}
    for line in section(SKILL_DIR / "models.md", "Choosing a roster").splitlines():
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        choice = next((c for c in ROSTER_CHOICES if f"`{c}`" in line), None)
        if line.startswith("|") and choice and len(cells) == 3:
            files = [path or shipped for path, shipped in ROSTER_FILE.findall(cells[1])]
            table[choice] = (cells[0], files, cells[2].strip("`"))
    return table


def frontmatter_description(text: str) -> str:
    match = re.search(r"^description: (.+)$", text.split("---")[1], re.MULTILINE)
    if match is None:
        raise AssertionError("frontmatter has no single-line description")
    return match.group(1)


class ReferencesResolve(unittest.TestCase):
    def test_every_relative_link_and_anchor_resolves(self):
        for doc in [*skill_docs(), *agent_files(), REPO / "README.md"]:
            for target in LINK.findall(strip_code_fences(read(doc))):
                if re.match(r"^[a-z]+:", target):
                    continue
                file_part, _, anchor = target.partition("#")
                linked = (doc.parent / file_part).resolve() if file_part else doc
                with self.subTest(doc=doc.relative_to(REPO).as_posix(), link=target):
                    self.assertTrue(linked.exists(), f"{target} points at a missing file")
                    if anchor and linked.suffix == ".md":
                        self.assertIn(anchor, anchors_in(linked), f"{target} points at a missing heading")

    def test_every_script_and_step_reference_exists(self):
        for doc in [*skill_docs(), *agent_files(), REPO / "README.md"]:
            text = read(doc)
            for script in SCRIPT.findall(text):
                with self.subTest(doc=doc.name, script=script):
                    self.assertTrue((REPO / script).is_file(), f"{script} does not exist")
            for reference in STEP_REFERENCE.findall(text):
                with self.subTest(doc=doc.name, reference=reference):
                    self.assertTrue((SKILL_DIR / reference).is_file(), f"{reference} does not exist")

    def test_every_worker_named_has_an_agent_file(self):
        known = {path.stem for path in agent_files()} | NOT_WORKERS
        for doc in [*skill_docs(), *agent_files(), REPO / "README.md"]:
            for line in read(doc).splitlines():
                for name in set(WORKER.findall(line)):
                    with self.subTest(doc=doc.name, worker=name):
                        if name in REMOVED_AGENTS and doc in OLDER_INSTALL_DOCS:
                            self.assertIn("older install", line)
                        else:
                            self.assertIn(name, known)

    def test_the_roster_lists_every_agent(self):
        roster = read(SKILL_DIR / "references" / "workers.md")
        for agent in agent_files():
            with self.subTest(agent=agent.stem):
                self.assertIn(f"`{agent.stem}`", roster)


class PlaybookSteps(unittest.TestCase):
    def test_every_playbook_has_a_steps_checklist(self):
        for playbook in playbooks():
            with self.subTest(playbook=playbook.name):
                self.assertTrue(checklist(playbook))

    def test_tracks_that_change_code_launch_implementer_and_verifier_as_steps(self):
        # The ledger check refuses a skip on implement or verify, nested or not.
        for track in TRACKS_THAT_CHANGE_CODE:
            steps = "\n".join(checklist(SKILL_DIR / "playbooks" / f"{track}.md"))
            for worker in ("supercook-implementer", "supercook-verifier"):
                with self.subTest(track=track, worker=worker):
                    self.assertIn(f": {worker}", steps)

    def test_a_slice_block_verifies_the_slice_before_its_pr_opens(self):
        for playbook in playbooks():
            block = [line for line in checklist(playbook) if line.startswith("  - [ ] slice <n>")]
            if not block:
                continue
            with self.subTest(playbook=playbook.name):
                verify = next(i for i, line in enumerate(block) if ": supercook-verifier" in line)
                pr = next(i for i, line in enumerate(block) if " PR opens" in line)
                self.assertLess(verify, pr)
                self.assertEqual(pr, len(block) - 1)

    def test_investigation_launches_the_explorer_as_a_step(self):
        steps = "\n".join(checklist(SKILL_DIR / "playbooks" / "investigation.md"))
        self.assertIn(": supercook-explorer", steps)


class LaunchRule(unittest.TestCase):
    def test_parallel_launches_are_never_backgrounded(self):
        # A background result arrives only after the turn ends, which the continuation rules forbid.
        launch = read(SKILL_DIR / "SKILL.md").split("## Launching a worker", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Never set `run_in_background`", launch)
        for doc in [*skill_docs(), *agent_files(), REPO / "README.md"]:
            if doc != SKILL_DIR / "SKILL.md":
                with self.subTest(doc=doc.relative_to(REPO).as_posix()):
                    self.assertNotIn("run_in_background", read(doc))


class RosterChoice(unittest.TestCase):
    def test_start_takes_the_roster_choice_off_the_ask_before_routing(self):
        steps = re.findall(r"^\d+\. .*$", section(SKILL_DIR / "SKILL.md", "Start"), re.MULTILINE)
        roster = next(i for i, step in enumerate(steps) if all(f"`{c}`" in step for c in ROSTER_CHOICES))
        route = next(i for i, step in enumerate(steps) if step.split(". ", 1)[1].startswith("Route the ask"))
        self.assertLess(roster, route)
        self.assertIn("(models.md#choosing-a-roster)", steps[roster])

    def test_no_choice_and_roster_repo_keep_the_three_tier_merge(self):
        ask, files, ledger = roster_choices()["roster:repo"]
        self.assertIn("nothing", ask)
        self.assertEqual(files, [REPO_ROSTER, HOME_ROSTER, SHIPPED_ROSTER])
        self.assertEqual(ledger, "roster: repo")

    def test_roster_local_ignores_the_repo_file_and_falls_back_to_shipped(self):
        _, files, ledger = roster_choices()["roster:local"]
        self.assertEqual(files, [HOME_ROSTER, SHIPPED_ROSTER])
        self.assertEqual(ledger, "roster: local")

    def test_the_ledger_version_line_records_the_version_and_the_roster(self):
        line = VERSION_LINE.search(read(SKILL_DIR / "references" / "ledger.md"))
        self.assertIsNotNone(line, "the ledger example has no `supercook: <v> from <root> | roster: <r>` line")
        manifest = json.loads(read(REPO / ".cursor-plugin" / "plugin.json"))
        self.assertEqual(line.group(1), manifest["version"])
        self.assertIn(f"roster: {line.group(2)}", {ledger for _, _, ledger in roster_choices().values()})


class SizeBudgets(unittest.TestCase):
    def assert_at_most(self, paths, limit):
        for path in paths:
            with self.subTest(doc=path.relative_to(REPO).as_posix()):
                self.assertLessEqual(len(read(path).split()), limit)

    def test_every_skill_md_stays_near_pstack_size(self):
        self.assert_at_most(SKILL_FILES, MAX_SKILL_WORDS)

    def test_playbooks_stay_short(self):
        self.assert_at_most(playbooks(), MAX_PLAYBOOK_WORDS)

    def test_references_and_agents_stay_short(self):
        self.assert_at_most(sorted((SKILL_DIR / "references").glob("*.md")), MAX_REFERENCE_WORDS)
        self.assert_at_most(agent_files(), MAX_AGENT_WORDS)


class Packaging(unittest.TestCase):
    def test_every_agent_file_name_matches_its_frontmatter_name(self):
        for agent in agent_files():
            with self.subTest(agent=agent.name):
                self.assertIn(f"\nname: {agent.stem}\n", read(agent))

    def test_descriptions_stay_loadable_frontmatter(self):
        for described in [*SKILL_FILES, *agent_files()]:
            description = frontmatter_description(read(described))
            with self.subTest(file=described.name):
                self.assertLessEqual(len(description), MAX_DESCRIPTION_CHARS)
                for breaker in YAML_PLAIN_SCALAR_BREAKERS:
                    self.assertNotIn(breaker, description)

    def test_plugin_manifest_has_a_semver_version(self):
        manifest = json.loads(read(REPO / ".cursor-plugin" / "plugin.json"))
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")

    def test_every_skill_frontmatter_names_its_directory(self):
        for skill in SKILL_FILES:
            with self.subTest(skill=skill.parent.name):
                self.assertIn(f"\nname: {skill.parent.name}\n", read(skill))


class LedgerCheckSeesEveryWorkerStep(unittest.TestCase):
    def test_every_worker_row_in_every_playbook_parses_to_known_roles(self):
        known = {path.stem for path in agent_files()}
        for playbook in playbooks():
            rows = checklist(playbook)
            parsed = {row.text: row.roles for row in run_folder.steps("## Steps\n" + "\n".join(rows))}
            for line in rows:
                if ": supercook-" in line:
                    text = line.split("] ", 1)[1].strip()
                    with self.subTest(playbook=playbook.name, step=text[:60]):
                        self.assertTrue(parsed.get(text), "the ledger check would not see this worker row")
                        self.assertLessEqual(set(parsed[text]), known)


if __name__ == "__main__":
    unittest.main()
