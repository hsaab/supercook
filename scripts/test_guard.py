"""Journeys for scripts/guard.py. Run: python3 -m unittest discover -s scripts

Each test builds a throwaway git repo and runs the script in it, the way the
supercook parent runs it after a worker returns.
"""

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "guard.py"
STUB_CHECK = "python3 -c \"import os, sys; sys.exit(1 if os.path.exists('stub.py') else 0)\""


class GuardRepo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.write("src/app.py", "def handler():\n    return 1\n")
        self.write("src/app_test.py", "assert True\n")
        self.write("README.md", "readme\n")
        self.commit("initial")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout

    def write(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()

    def guard(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=self.repo, capture_output=True, text=True
        )


class ScopeAfterImplementer(GuardRepo):
    def test_changes_inside_the_slice_pass(self) -> None:
        self.write("src/app.py", "def handler():\n    return 2\n")
        result = self.guard("scope", "--allow", "src/app.py", "--tests", "**/*_test.py")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("scope: ok", result.stdout)

    def test_a_file_outside_the_slice_is_named(self) -> None:
        self.write("src/app.py", "def handler():\n    return 2\n")
        self.write("README.md", "rewritten\n")
        result = self.guard("scope", "--allow", "src/app.py", "--tests", "**/*_test.py")
        self.assertEqual(result.returncode, 1)
        self.assertIn("out of scope: README.md", result.stdout)

    def test_fix_restores_an_edited_test_and_deletes_an_added_one(self) -> None:
        self.write("src/app_test.py", "assert False\n")
        self.write("src/new_test.py", "assert True\n")
        result = self.guard("scope", "--allow", "src/", "--tests", "**/*_test.py", "--fix")
        self.assertEqual(result.returncode, 1)
        self.assertIn("restored test src/app_test.py", result.stdout)
        self.assertIn("deleted added test src/new_test.py", result.stdout)
        self.assertEqual((self.repo / "src/app_test.py").read_text(), "assert True\n")
        self.assertFalse((self.repo / "src/new_test.py").exists())
        self.assertEqual(self.guard("scope", "--allow", "src/", "--tests", "**/*_test.py").returncode, 0)

    def test_a_test_committed_after_the_test_commit_fails(self) -> None:
        tests_sha = self.git("rev-parse", "HEAD").strip()
        self.write("src/app_test.py", "assert 1 == 1\n")
        self.commit("bend the test")
        result = self.guard("scope", "--allow", "src/", "--tests", "**/*_test.py", "--since", tests_sha)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"test committed after {tests_sha}: src/app_test.py", result.stdout)

    def test_base_mode_checks_everything_committed_on_the_branch(self) -> None:
        self.git("checkout", "-q", "-b", "slice")
        self.write("docs/notes.md", "stray\n")
        self.commit("stray file")
        result = self.guard("scope", "--allow", "src/", "--base", "main")
        self.assertEqual(result.returncode, 1)
        self.assertIn("out of scope since main: docs/notes.md", result.stdout)

    def test_run_folder_is_never_out_of_scope(self) -> None:
        self.write(".supercook/run/ledger.md", "# Ledger\n")
        self.assertEqual(self.guard("scope", "--allow", "src/").returncode, 0)


class RedAfterTestDesigner(GuardRepo):
    def stub_patch(self) -> Path:
        self.write("stub.py", "def handler():\n    raise NotImplementedError\n")
        self.git("add", "-N", "stub.py")
        patch = self.repo / ".supercook" / "red-stub.patch"
        patch.parent.mkdir(exist_ok=True)
        patch.write_text(self.git("diff", "--", "stub.py"), encoding="utf-8")
        self.git("rm", "-q", "--cached", "stub.py")
        (self.repo / "stub.py").unlink()
        return patch

    def test_red_is_confirmed_and_the_stub_reverses(self) -> None:
        patch = self.stub_patch()
        result = self.guard("red", "--cmd", STUB_CHECK, "--patch", str(patch))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("red: confirmed", result.stdout)
        self.assertFalse((self.repo / "stub.py").exists())

    def test_a_suite_that_passes_is_not_red(self) -> None:
        result = self.guard("red", "--cmd", STUB_CHECK)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not red", result.stdout)

    def test_a_patch_that_does_not_apply_fails(self) -> None:
        patch = self.stub_patch()
        self.write("stub.py", "already here\n")
        result = self.guard("red", "--cmd", STUB_CHECK, "--patch", str(patch))
        self.assertEqual(result.returncode, 1)
        self.assertIn("stub patch does not apply", result.stdout)


class LinesBeforeAPullRequest(GuardRepo):
    def test_lockfiles_count_as_raw_but_not_reviewable(self) -> None:
        self.git("checkout", "-q", "-b", "slice")
        self.write("src/app.py", "def handler():\n    return 2\n")
        self.write("package-lock.json", "\n".join(str(n) for n in range(50)) + "\n")
        self.commit("slice")
        result = self.guard("lines", "--base", "main")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("reviewable: 2 | raw: 52", result.stdout)

    def test_over_budget_fails(self) -> None:
        self.git("checkout", "-q", "-b", "slice")
        self.write("src/big.py", "\n".join(f"x{n} = {n}" for n in range(30)) + "\n")
        self.commit("big")
        result = self.guard("lines", "--base", "main", "--budget", "20")
        self.assertEqual(result.returncode, 1)
        self.assertIn("over budget", result.stdout)


class RecipeIntegrity(GuardRepo):
    def test_recorded_hash_matches_until_the_recipe_changes(self) -> None:
        recipe = self.repo / "recipe.md"
        recipe.write_text("1. curl /health\n", encoding="utf-8")
        recorded = hashlib.sha256(recipe.read_bytes()).hexdigest()
        self.assertEqual(self.guard("recipe", str(recipe), "--sha", recorded).returncode, 0)
        recipe.write_text("1. skip it\n", encoding="utf-8")
        result = self.guard("recipe", str(recipe), "--sha", recorded)
        self.assertEqual(result.returncode, 1)
        self.assertIn("changed since it was recorded", result.stdout)


if __name__ == "__main__":
    unittest.main()
