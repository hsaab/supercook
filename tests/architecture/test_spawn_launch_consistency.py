"""Pins launch-doc lines that still disagree with the roster launch rule.

Run with: python3 -m unittest discover -s tests/architecture

The numbered spawn path is pinned by the words "spawn shape" on the path 2
line and on the tool-name table row. A link to #start-here-the-launch-rule
is not the check: path 2 already sits under that heading, so a self-link
would not show that the line defers to the field rule.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DOC = "skills/supercook/SKILL.md"
AGENTS_DOC = "skills/supercook/agents.md"
SKILL_TREE = Path("skills/supercook")
LAUNCH_RULE_HEADING = "## Start here: the launch rule"
PLUGIN_LAUNCH_FILE = ".cursor/supercook/subagent-launch.md"
REPO_AGENTS_DIR = ".cursor/agents/"
HOME_AGENTS_DIR = "~/.cursor/agents/"
FORBIDDEN_GUIDE_TIMING = "before opening that phase's guide"
SPAWN_SHAPE_WORDS = "spawn shape"

# Link targets only. A backtick or plain-text mention of the same path stays allowed.
INLINE_LINK_TARGET = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)")
REFERENCE_LINK_TARGET = re.compile(r"^\s{0,3}\[[^\]\n]+\]:[ \t]+(\S+)", re.MULTILINE)


def read_doc(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def section_body(text: str, heading: str) -> str:
    """Return the text between a level-two heading and the next level-two heading."""
    start = text.index(heading) + len(heading)
    next_heading = re.search(r"^## ", text[start:], flags=re.MULTILINE)
    return text[start:] if next_heading is None else text[start : start + next_heading.start()]


def sentences_of(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def line_with(text: str, marker: str) -> str:
    """Return the single physical line that contains marker."""
    matches = [line for line in text.splitlines() if marker in line]
    if len(matches) != 1:
        raise AssertionError(f"expected one line containing {marker!r}, found {len(matches)}")
    return matches[0]


def list_item(text: str, marker: str) -> str:
    """Return the list item that contains marker, including wrapped continuation lines."""
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if marker in line), None)
    if start is None:
        raise AssertionError(f"missing list item: {marker}")
    parts = [lines[start].strip()]
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("- ", "* ", "#")) or re.match(r"^\d+\. ", stripped):
            break
        parts.append(stripped)
    return " ".join(parts)


def table_cells(text: str, first_cell: str) -> list[str]:
    """Return the stripped cells of the unique table row whose first cell matches."""
    found = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == first_cell:
            found.append(cells)
    if len(found) != 1:
        raise AssertionError(f"expected one {first_cell} row, found {len(found)}")
    return found[0]


def column_named(text: str, first_cell: str, header_marker: str, column_name: str) -> str:
    """Return one cell, looked up by the table header so a reordered column still resolves."""
    header = line_with(text, header_marker)
    headers = [cell.strip() for cell in header.strip().strip("|").split("|")]
    cells = table_cells(text, first_cell)
    if column_name not in headers:
        raise AssertionError(f"{header_marker} table has no {column_name} column")
    return cells[headers.index(column_name)]


def markdown_link_targets(text: str) -> list[str]:
    """Inline and reference-definition targets. Plain text is not a target."""
    return INLINE_LINK_TARGET.findall(text) + REFERENCE_LINK_TARGET.findall(text)


class SpawnLaunchConsistencyTest(unittest.TestCase):
    def test_host_recipe_last_branch_matches_the_launch_rule(self):
        """The Name the worker Otherwise branch is general-purpose only, with no explore type."""
        item = list_item(read_doc(AGENTS_DOC), "**Name the worker.**")
        otherwise = [sentence for sentence in sentences_of(item) if sentence.startswith("Otherwise")]
        self.assertEqual(len(otherwise), 1, "Name the worker recipe has no single Otherwise branch")
        branch = otherwise[0]
        self.assertIn("general-purpose", branch)
        self.assertNotIn("explore", branch, "Otherwise branch still offers an explore type: " + branch)

    def test_numbered_spawn_path_defers_to_the_spawn_shape_rule(self):
        """Path 2 and the tool-name row must contain the words "spawn shape"."""
        targets = (
            ("SKILL.md path 2", line_with(read_doc(SKILL_DOC), "2. **Any listed spawn tool.**")),
            ("agents.md tool-name row", line_with(read_doc(AGENTS_DOC), "| `<tool name>` |")),
        )
        for label, line in targets:
            with self.subTest(line=label):
                self.assertIn(
                    SPAWN_SHAPE_WORDS,
                    line.casefold(),
                    f"{label} still states the named recipe without pointing at the spawn shape rule",
                )

    def test_launch_rule_and_guide_reading_line_agree(self):
        """The parent may read a phase guide to write the brief, and must not do the phase."""
        skill = read_doc(SKILL_DOC)
        rule = section_body(skill, LAUNCH_RULE_HEADING)
        with self.subTest(check="launch is not before opening the guide"):
            hits = [
                index
                for index, line in enumerate(skill.splitlines(), start=1)
                if FORBIDDEN_GUIDE_TIMING in line
            ]
            self.assertEqual(
                hits,
                [],
                "SKILL.md still says the next launch comes before opening that phase's guide, on lines "
                + ", ".join(str(index) for index in hits),
            )
        with self.subTest(check="guide is read to write the brief"):
            matching = [
                sentence
                for sentence in sentences_of(rule)
                if "guide" in sentence and "to write" in sentence and "brief" in sentence
            ]
            self.assertTrue(
                matching,
                "launch rule has no sentence that reads the guide to write the brief",
            )

    def test_no_skill_link_resolves_to_the_plugin_launch_file(self):
        """No markdown link target under skills/supercook may contain the plugin launch path."""
        files = sorted((REPO_ROOT / SKILL_TREE).glob("**/*.md"))
        self.assertTrue(files, "skills/supercook has no markdown files")
        violations = []
        for path in files:
            relative = path.relative_to(REPO_ROOT).as_posix()
            for target in markdown_link_targets(path.read_text(encoding="utf-8")):
                if PLUGIN_LAUNCH_FILE in target:
                    violations.append(f"{relative} -> {target}")
        self.assertEqual(
            violations,
            [],
            "a skill markdown link target still points at .cursor/supercook/subagent-launch.md",
        )

    def test_typed_spawn_path_names_the_repo_agents_dir(self):
        """The typed When cell must name the repo .cursor/agents/, not only the home directory."""
        when = column_named(read_doc(AGENTS_DOC), "`typed`", "| `spawn:` |", "When")
        # ~/.cursor/agents/ contains the repo spelling as a suffix, so strip the home path first.
        without_home = when.replace(HOME_AGENTS_DIR, "")
        self.assertIn(
            REPO_AGENTS_DIR,
            without_home,
            "typed When cell names ~/.cursor/agents/ and not the repo .cursor/agents/: " + when,
        )


if __name__ == "__main__":
    unittest.main()
