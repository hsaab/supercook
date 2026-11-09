"""Guards the launch docs against pinning one host's spawn tool. Run with: python3 -m unittest discover -s tests/architecture

Coordinators must launch named supercook-<role> subagents through whatever spawn tool their session lists,
so no launch doc may name a single host tool (such as task_v2) as the required path.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_DOCS = (
    "README.md",
    "skills/supercook/SKILL.md",
    "skills/supercook/agents.md",
    "skills/supercook/pipeline/intake.md",
    "skills/supercook/references/coordinator-kickoff.md",
    ".cursor/rules/supercook-subagent-launch.mdc",
    ".cursor/supercook/subagent-launch.md",
)
PINNED_TOOL_NAMES = ("task_v2",)


def read_doc(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class SpawnLaunchDocsTest(unittest.TestCase):
    def test_no_launch_doc_pins_a_host_specific_spawn_tool(self):
        for relative_path in LAUNCH_DOCS:
            text = read_doc(relative_path)
            for tool_name in PINNED_TOOL_NAMES:
                with self.subTest(doc=relative_path, tool=tool_name):
                    self.assertNotIn(tool_name, text)

    def test_agents_doc_keeps_named_launch_and_inline_fallback(self):
        text = read_doc("skills/supercook/agents.md")
        self.assertIn("/supercook-<role>", text)
        self.assertIn("| `none` | No nested-spawn tool of any kind |", text)
        self.assertIn("### Forbidden skips", text)

    def test_every_agent_file_declares_its_supercook_name(self):
        agent_files = sorted((REPO_ROOT / "agents").glob("supercook-*.md"))
        self.assertEqual(len(agent_files), 9)
        for agent_file in agent_files:
            with self.subTest(agent=agent_file.name):
                frontmatter = agent_file.read_text(encoding="utf-8").split("---")[1]
                self.assertIn(f"name: {agent_file.stem}", frontmatter)


if __name__ == "__main__":
    unittest.main()
