"""Journeys for scripts/guard.py. Run: python3 -m unittest discover -s scripts

Each test builds a throwaway git repo and runs the script in it, the way the
supercook parent runs it after a worker returns.
"""

import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "guard.py"
PYTHON = shlex.quote(sys.executable)
# Fails on the journey assertion with the stub in place, and at import without it.
SUITE = PYTHON + (
    " -c \"import os, sys;"
    " sys.exit('FAILED test_handler' if os.path.exists('stub.py') else 'ModuleNotFoundError: stub')\""
)
# Host git config (this VM sets core.quotepath=false) would hide quoting bugs.
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


class GuardRepo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        (self.repo / ".git" / "info" / "exclude").write_text(".supercook/\n", encoding="utf-8")
        self.write("src/app.py", "def handler():\n    return 1\n")
        self.write("src/app_test.py", "assert True\n")
        self.write("README.md", "readme\n")
        self.start = self.commit("initial")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo, env=ENV, check=True, capture_output=True, text=True
        ).stdout

    def write(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read(self, relative: str) -> str:
        return (self.repo / relative).read_text(encoding="utf-8")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()

    def guard(self, *args: str, cwd: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=self.repo / cwd, env=ENV, capture_output=True, text=True
        )

    def assertExit(self, result: subprocess.CompletedProcess, code: int) -> None:
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)

    def scope(self, *args: str, cwd: str = "") -> subprocess.CompletedProcess:
        tests = ("--tests", "**/*_test.py", "--since", self.start)
        return self.guard("scope", "--allow", "src/", *tests, *args, cwd=cwd)


class ScopeAfterImplementer(GuardRepo):
    def test_changes_inside_the_slice_pass(self) -> None:
        self.write("src/app.py", "def handler():\n    return 2\n")
        result = self.scope()
        self.assertExit(result, 0)
        self.assertIn("scope: ok", result.stdout)

    def test_a_file_outside_the_slice_is_named(self) -> None:
        self.write("README.md", "rewritten\n")
        result = self.scope()
        self.assertExit(result, 1)
        self.assertIn("out of scope: README.md", result.stdout)

    def test_fix_undoes_every_kind_of_test_change_and_names_each_one(self) -> None:
        self.git("mv", "src/app_test.py", "src/moved_test.py")
        self.write("src/moved_test.py", "assert 1\n")
        self.write("src/staged_test.py", "assert True\n")
        self.git("add", "src/staged_test.py")
        self.write("src/staged_test.py", "assert 2\n")
        self.write("src/new_test.py", "assert True\n")
        result = self.scope("--fix")
        self.assertExit(result, 1)
        for line in ("restored test src/app_test.py", "deleted added test src/moved_test.py",
                     "deleted added test src/staged_test.py", "deleted added test src/new_test.py"):
            self.assertIn(line, result.stdout)
        self.assertEqual(self.read("src/app_test.py"), "assert True\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertExit(self.scope(), 0)

    def test_a_committed_test_edit_fails_and_fix_restores_it_from_since(self) -> None:
        self.write("src/app_test.py", "assert 1 == 1\n")
        self.commit("bend the test")
        self.assertIn("test changed: src/app_test.py", self.scope().stdout)
        self.assertIn("restored test src/app_test.py", self.scope("--fix").stdout)
        self.assertEqual(self.read("src/app_test.py"), "assert True\n")
        self.assertExit(self.scope(), 0)

    def test_a_committed_rename_away_from_the_test_globs_fails(self) -> None:
        self.git("mv", "src/app_test.py", "src/app_helper.py")
        self.commit("hide the test")
        result = self.scope()
        self.assertExit(result, 1)
        self.assertIn("test changed: src/app_test.py", result.stdout)

    def test_a_non_ascii_test_name_is_not_quoted_past_the_globs(self) -> None:
        self.write("src/café_test.py", "assert True\n")
        self.start = self.commit("tests")
        self.write("src/café_test.py", "assert 1\n")
        self.commit("bend it")
        self.assertIn("test changed: src/café_test.py", self.scope().stdout)

    def test_since_without_tests_still_checks_committed_scope(self) -> None:
        self.write("README.md", "rewritten\n")
        self.commit("stray")
        result = self.guard("scope", "--allow", "src/", "--since", self.start)
        self.assertExit(result, 1)
        self.assertIn("out of scope: README.md", result.stdout)

    def test_globs_follow_git_pathspec_rules(self) -> None:
        self.write("src/foo.test.ts", "it('works')\n")
        self.start = self.commit("ts test")
        self.write("src/foo.test.ts", "it.skip('works')\n")
        self.write("src/deep/x.py", "x = 1\n")
        self.write("app/[id]/page.tsx", "page\n")
        self.write("app/i/page.tsx", "other\n")
        cases = [
            # A middle **/ matches zero folders.
            (["--allow", "src/", "app/", "--tests", "src/**/*.test.ts"], "test changed: src/foo.test.ts"),
            # * stays inside one folder.
            (["--allow", "src/*.py", "src/*.ts", "app/"], "out of scope: src/deep/x.py"),
            # A path with no * or ? is literal, so [id] is not a character class.
            (["--allow", "src/", "app/[id]/page.tsx"], "out of scope: app/i/page.tsx"),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                result = self.guard("scope", "--since", self.start, *args)
                self.assertExit(result, 1)
                self.assertIn(expected, result.stdout)
                self.assertEqual(result.stdout.count("\n"), 2, result.stdout)

    def test_running_from_a_subfolder_acts_on_repo_paths(self) -> None:
        self.write("pkg/src/new_test.py", "assert True\n")
        self.start = self.commit("unrelated package")
        self.write("src/new_test.py", "assert True\n")
        self.write("src/app_test.py", "assert False\n")
        result = self.scope("--fix", cwd="pkg")
        self.assertIn("deleted added test src/new_test.py", result.stdout)
        self.assertIn("restored test src/app_test.py", result.stdout)
        self.assertFalse((self.repo / "src/new_test.py").exists())
        self.assertTrue((self.repo / "pkg/src/new_test.py").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_base_mode_checks_everything_committed_on_the_branch(self) -> None:
        self.git("checkout", "-q", "-b", "slice")
        self.write("docs/notes.md", "stray\n")
        self.write("src/app_test.py", "assert 2\n")
        self.commit("stray file and the slice's test")
        result = self.guard("scope", "--allow", "src/app.py", "--tests", "**/*_test.py", "--base", "main")
        self.assertExit(result, 1)
        self.assertIn("out of scope: docs/notes.md", result.stdout)
        self.assertNotIn("app_test", result.stdout)

    def test_run_folders_and_the_setup_rule_are_exempt_but_the_tracked_roster_is_not(self) -> None:
        self.write(".supercook/models.md", "implementer: strong\n")
        self.git("add", "-f", ".supercook/models.md")
        self.start = self.commit("roster")
        self.write(".supercook/run/ledger.md", "# Ledger\n")
        self.write(".cursor/rules/supercook-delegation.mdc", "---\nalwaysApply: true\n---\n")
        self.assertExit(self.scope(), 0)
        self.git("add", "-f", ".supercook/run/ledger.md")
        self.commit("keep ledger")
        self.write(".supercook/models.md", "implementer: cheap\n")
        result = self.scope()
        self.assertExit(result, 1)
        self.assertEqual(result.stdout.splitlines()[0], "out of scope: .supercook/models.md")

    def test_misuse_and_bad_refs_exit_2_not_1(self) -> None:
        self.assertExit(self.guard("scope", "--allow", "src/", "--since", self.start, "--fix"), 2)
        self.assertExit(self.guard("scope", "--allow", "src/"), 2)
        result = self.guard("scope", "--allow", "src/", "--base", "no-such-ref")
        self.assertExit(result, 2)
        self.assertIn("guard: git merge-base", result.stderr)


class RedAfterTestDesigner(GuardRepo):
    def stub_patch(self, stub: str = "stub.py", text: str = "def handler():\n    return None\n") -> str:
        self.write(stub, text)
        self.git("add", "-N", stub)
        patch = self.repo / ".supercook" / "red-stub.patch"
        patch.parent.mkdir(exist_ok=True)
        patch.write_text(self.git("diff"), encoding="utf-8")
        self.git("reset", "-q", "--hard")
        (self.repo / stub).unlink(missing_ok=True)
        return str(patch)

    def red(self, *args: str, cmd: str = SUITE, cwd: str = "") -> subprocess.CompletedProcess:
        return self.guard("red", "--cmd", cmd, "--expect", "FAILED test_handler", "--tests", "**/*_test.py",
                          *args, cwd=cwd)

    def test_red_is_confirmed_and_the_stub_reverses(self) -> None:
        result = self.red("--patch", self.stub_patch(), "--stub", "stub.py")
        self.assertExit(result, 0)
        self.assertIn("red: confirmed", result.stdout)
        self.assertFalse((self.repo / "stub.py").exists())

    def test_red_from_a_subfolder_still_applies_the_stub(self) -> None:
        patch = os.path.relpath(self.stub_patch(), self.repo / "src")
        self.assertExit(self.red("--patch", patch, "--stub", "stub.py", cwd="src"), 0)

    def test_a_suite_that_passes_is_not_red(self) -> None:
        result = self.red(cmd=f"{PYTHON} -c pass")
        self.assertExit(result, 1)
        self.assertIn("not red", result.stdout)

    def test_failing_for_the_wrong_reason_is_not_red(self) -> None:
        result = self.red()
        self.assertExit(result, 1)
        self.assertIn("lacks: FAILED test_handler", result.stdout)

    def test_a_command_that_cannot_run_is_not_red(self) -> None:
        result = self.red(cmd="pytset -q")
        self.assertExit(result, 2)
        self.assertIn("could not run (exit 127)", result.stdout)

    def test_a_timeout_is_reported_as_not_run(self) -> None:
        result = self.red("--timeout", "1", cmd="sleep 30 | cat")
        self.assertExit(result, 2)
        self.assertIn("red: timed out after 1s", result.stdout)

    def test_a_patch_that_does_not_apply_fails(self) -> None:
        patch = self.stub_patch()
        self.write("stub.py", "already here\n")
        result = self.red("--patch", patch, "--stub", "stub.py")
        self.assertExit(result, 1)
        self.assertIn("stub patch does not apply", result.stdout)

    def test_a_patch_that_also_edits_a_test_is_refused(self) -> None:
        self.write("src/app_test.py", "assert False\n")
        patch = self.stub_patch()
        result = self.red("--patch", patch, "--stub", "stub.py", cmd=f"{PYTHON} src/app_test.py")
        self.assertExit(result, 1)
        self.assertIn("outside --stub: src/app_test.py", result.stdout)
        self.assertEqual(self.read("src/app_test.py"), "assert True\n")

    def test_a_stub_path_that_is_a_test_is_refused(self) -> None:
        patch = self.stub_patch("src/zz_test.py", "assert False, 'FAILED test_handler'\n")
        result = self.red("--patch", patch, "--stub", "src/zz_test.py")
        self.assertExit(result, 1)
        self.assertIn("a --stub path matches the test globs", result.stdout)
        self.assertFalse((self.repo / "src/zz_test.py").exists())

    def test_a_stub_left_in_the_tree_fails(self) -> None:
        self.write("stub.py", "def handler():\n    return None\n")
        result = self.red()
        self.assertExit(result, 1)
        self.assertIn("only test paths may stay changed, found: stub.py", result.stdout)


class LinesBeforeAPullRequest(GuardRepo):
    def test_lockfiles_count_as_raw_but_not_reviewable(self) -> None:
        self.git("checkout", "-q", "-b", "slice")
        self.write("src/app.py", "def handler():\n    return 2\n")
        self.write("package-lock.json", "\n".join(str(n) for n in range(50)) + "\n")
        self.commit("slice")
        result = self.guard("lines", "--base", "main")
        self.assertExit(result, 0)
        self.assertIn("reviewable: 2 | raw: 52", result.stdout)

    def test_counts_match_the_line_accounting_pathspecs(self) -> None:
        self.write("deps/a.lock", "l\n" * 5)
        self.write("src/api_generated.py", "g\n" * 10)
        self.commit("generated code")
        self.git("checkout", "-q", "-b", "slice")
        self.git("mv", "deps/a.lock", "deps/b.lock")
        self.git("mv", "src/api_generated.py", "src/api.py")
        self.write("app/vendor/pricing.py", "p\n" * 4)
        self.write("vendor/lib.js", "v\n" * 6)
        self.commit("slice")
        self.write("src/new.py", "n\n" * 3)
        result = self.guard("lines", "--base", "main")
        # Reviewable: api.py 10, the nested vendor folder 4, the untracked file 3.
        self.assertIn("reviewable: 17 | raw: 43", result.stdout)

    def test_over_budget_fails(self) -> None:
        self.git("checkout", "-q", "-b", "slice")
        self.write("src/big.py", "\n".join(f"x{n} = {n}" for n in range(30)) + "\n")
        self.commit("big")
        result = self.guard("lines", "--base", "main", "--budget", "20")
        self.assertExit(result, 1)
        self.assertIn("over budget", result.stdout)


class RecipeIntegrity(GuardRepo):
    def test_recorded_hash_matches_until_the_recipe_changes(self) -> None:
        recipe = self.repo / "recipe.md"
        recipe.write_text("1. curl /health\n", encoding="utf-8")
        recorded = hashlib.sha256(recipe.read_bytes()).hexdigest()
        self.assertIn(recorded, self.guard("recipe", "hash", str(recipe)).stdout)
        self.assertExit(self.guard("recipe", "check", str(recipe), recorded), 0)
        recipe.write_text("1. skip it\n", encoding="utf-8")
        result = self.guard("recipe", "check", str(recipe), recorded)
        self.assertExit(result, 1)
        self.assertIn("changed since it was recorded", result.stdout)

    def test_an_unset_hash_is_an_error_and_a_deleted_recipe_fails(self) -> None:
        self.assertExit(self.guard("recipe", "check", "recipe.md", ""), 2)
        result = self.guard("recipe", "check", "recipe.md", "0" * 64)
        self.assertExit(result, 1)
        self.assertIn("recipe.md is missing", result.stdout)


class LedgerBeforeDelivery(GuardRepo):
    """Smoke tests; the ledger check itself is tested in process in test_run_folder.py."""

    def seed(self, launched: list[str], later_steps: str = "") -> None:
        run = self.repo / ".supercook" / "run"
        run.mkdir(parents=True)
        steps = "- [x] map the code: supercook-explorer (Task)\n- [x] implement: supercook-implementer (Task)\n"
        steps += later_steps
        (run / "ledger.md").write_text(f"# Ledger\n\n## Steps\n{steps}\n## Log\n", encoding="utf-8")
        (run / "launches.jsonl").write_text("".join(json.dumps({"role": r}) + "\n" for r in launched), encoding="utf-8")
        (self.repo / ".supercook" / "active-run").write_text(".supercook/run/ledger.md\n", encoding="utf-8")

    def test_a_matching_log_passes_and_counts_by_role(self) -> None:
        self.seed(["supercook-explorer", "supercook-explorer", "supercook-implementer"])
        result = self.guard("ledger")
        self.assertExit(result, 0)
        self.assertIn("launched: explorer 2, implementer 1", result.stdout)

    def test_a_checked_step_nobody_launched_fails_from_a_subfolder_too(self) -> None:
        self.seed(["supercook-explorer"])
        result = self.guard("ledger", cwd="src")
        self.assertExit(result, 1)
        self.assertIn("checked with no logged launch or agent id: step 2", result.stdout)

    def test_a_relative_ledger_path_is_read_from_where_guard_ran(self) -> None:
        self.seed(["supercook-explorer", "supercook-implementer"])
        (self.repo / ".supercook" / "active-run").unlink()
        self.assertExit(self.guard("ledger", "--ledger", "../.supercook/run/ledger.md", cwd="src"), 0)

    def test_no_live_run_could_not_run_and_says_how_to_point_at_one(self) -> None:
        result = self.guard("ledger")
        self.assertExit(result, 2)
        self.assertIn("pass --ledger", result.stdout)


if __name__ == "__main__":
    unittest.main()
