"""Shared readers for the architecture doc tests."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "supercook"
README_DOC = "README.md"
SKILL_DOC = "skills/supercook/SKILL.md"
AGENTS_DOC = "skills/supercook/agents.md"
INTAKE_DOC = "skills/supercook/pipeline/intake.md"
LEDGER_DOC = "skills/supercook/pipeline/ledger.md"
ASSESS_DOC = "skills/supercook/pipeline/assess.md"
LAUNCH_RULE_HEADING = "## Start here: the launch rule"


def read_doc(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def agent_files() -> list[Path]:
    return sorted((REPO_ROOT / "agents").glob("supercook-*.md"))


def agent_names() -> set[str]:
    return {path.stem for path in agent_files()}


def skill_docs() -> list[Path]:
    return sorted(SKILL_DIR.rglob("*.md"))


def playbook_files() -> list[Path]:
    return sorted((SKILL_DIR / "playbooks").glob("*.md"))


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


def strip_code_fences(text: str) -> str:
    """Drop fenced blocks, so example links and headings inside them are not read as real ones."""
    return re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)


def steps_block(playbook_text: str) -> str:
    """Return the fenced checklist under a playbook's `## Steps` heading."""
    steps = section_body(playbook_text, "## Steps")
    match = re.search(r"^```\n(.*?)^```", steps, flags=re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError("## Steps has no fenced checklist")
    return match.group(1)
