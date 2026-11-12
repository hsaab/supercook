"""Runs the git-exclude snippet from intake.md against real temporary repos.

Run with: python3 -m unittest discover -s tests/architecture

The repo roster `.supercook/models.md` must stay visible to git (so cloud agents can get it)
while run artifacts under `.supercook/` stay ignored.
"""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INTAKE_DOC = REPO_ROOT / "skills/supercook/pipeline/intake.md"
EXCLUDE_ANCHOR = "Keep run artifacts out of git"
LEGACY_ENTRY = ".supercook/"
LINES = ("**/.supercook/*", "!**/.supercook/models.md")


def exclude_snippet() -> str:
    text = INTAKE_DOC.read_text(encoding="utf-8")
    after = text[text.index(EXCLUDE_ANCHOR) :]
    match = re.search(r"```bash\n(.*?)```", after, re.DOTALL)
    assert match is not None, "intake.md lost its exclude snippet"
    return match.group(1)


def run(cmd, cwd, **kwargs):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, **kwargs)


def run_snippet(cwd: Path) -> None:
    run(["bash", "-c", exclude_snippet()], cwd)


def is_ignored(cwd: Path, rel: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", rel], cwd=cwd).returncode == 0


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    run(["git", "init", "-q", "-b", "main"], repo)
    run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init"], repo)
    (repo / ".supercook" / "run-1").mkdir(parents=True)
    (repo / ".supercook" / "run-1" / "ledger.md").write_text("x")
    (repo / ".supercook" / "models.md").write_text("x")
    return repo


class IntakeExcludeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = make_repo(self.root)

    def exclude_lines(self, repo: Path) -> list[str]:
        path = run(["git", "rev-parse", "--git-path", "info/exclude"], repo).stdout.strip()
        return (repo / path).read_text().splitlines()

    def assert_roster_visible_artifacts_ignored(self):
        self.assertTrue(is_ignored(self.repo, ".supercook/run-1/ledger.md"))
        self.assertFalse(is_ignored(self.repo, ".supercook/models.md"))

    def test_fresh_repo_ignores_artifacts_but_not_roster(self):
        run_snippet(self.repo)
        self.assert_roster_visible_artifacts_ignored()

    def test_legacy_folder_entry_is_migrated(self):
        info = self.repo / ".git" / "info"
        info.mkdir(exist_ok=True)
        (info / "exclude").write_text("# keep\nnode_modules/\n.supercook/\n")
        self.assertTrue(is_ignored(self.repo, ".supercook/models.md"))

        run_snippet(self.repo)

        self.assert_roster_visible_artifacts_ignored()
        lines = self.exclude_lines(self.repo)
        self.assertNotIn(LEGACY_ENTRY, lines)
        self.assertIn("node_modules/", lines)

    def test_second_run_adds_nothing(self):
        run_snippet(self.repo)
        first = self.exclude_lines(self.repo)
        run_snippet(self.repo)
        second = self.exclude_lines(self.repo)
        self.assertEqual(first, second)
        for line in LINES:
            self.assertEqual(second.count(line), 1)

    def test_linked_worktree_writes_shared_exclude(self):
        worktree = self.root / "wt"
        run(["git", "worktree", "add", "-q", str(worktree), "-b", "feature"], self.repo)

        run_snippet(worktree)

        for line in LINES:
            self.assertIn(line, self.exclude_lines(self.repo))
        self.assert_roster_visible_artifacts_ignored()

    def test_subdirectory_workspace_ignores_artifacts_but_not_roster(self):
        pkg = self.repo / "pkg"
        (pkg / ".supercook" / "run-1").mkdir(parents=True)
        (pkg / ".supercook" / "run-1" / "ledger.md").write_text("x")
        (pkg / ".supercook" / "models.md").write_text("x")

        run_snippet(pkg)

        self.assertTrue(is_ignored(pkg, ".supercook/run-1/ledger.md"))
        self.assertFalse(is_ignored(pkg, ".supercook/models.md"))
        self.assert_roster_visible_artifacts_ignored()

    def test_bare_line_appended_by_older_plugin_is_migrated_again(self):
        run_snippet(self.repo)
        exclude = self.repo / ".git" / "info" / "exclude"
        with exclude.open("a") as handle:
            handle.write("\n.supercook/\n")
        self.assertTrue(is_ignored(self.repo, ".supercook/models.md"))

        run_snippet(self.repo)

        lines = self.exclude_lines(self.repo)
        self.assertNotIn(LEGACY_ENTRY, lines)
        for line in LINES:
            self.assertEqual(lines.count(line), 1)
        self.assert_roster_visible_artifacts_ignored()

    def test_symlinked_exclude_stays_a_symlink_and_target_gets_the_lines(self):
        target = self.root / "real_exclude"
        target.write_text("# shared by dotfiles\n")
        exclude = self.repo / ".git" / "info" / "exclude"
        exclude.unlink(missing_ok=True)
        exclude.parent.mkdir(exist_ok=True)
        exclude.symlink_to(target)

        run_snippet(self.repo)

        self.assertTrue(exclude.is_symlink())
        content = target.read_text().splitlines()
        self.assertIn("# shared by dotfiles", content)
        for line in LINES:
            self.assertIn(line, content)

    def test_hand_written_variants_are_left_alone(self):
        exclude = self.repo / ".git" / "info" / "exclude"
        exclude.parent.mkdir(exist_ok=True)
        exclude.write_text(".supercook\n/.supercook/\n")

        run_snippet(self.repo)

        lines = self.exclude_lines(self.repo)
        self.assertIn(".supercook", lines)
        self.assertIn("/.supercook/", lines)


if __name__ == "__main__":
    unittest.main()
