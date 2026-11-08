"""User-journey tests for scripts/validate_subagent_launch.py. Run with: python3 -m unittest discover -s tests/architecture

Unit cases call the validator functions directly; CLI cases run the script with subprocess from a fresh temp dir.
Every file lives in a temp dir, so nothing is written into the repo.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_subagent_launch.py"
MODULE_NAME = "validate_subagent_launch"

VERIFIER_PROMPT = (
    "supercook-role: standard\n"
    "supercook-run: /tmp/run\n"
    "\n"
    'Say "done" when C:\\work\\repo passes. It\'s fine.\n'
    "\ttabbed line, caf\u00e9 na\u00efve \u65e5\u672c\u8a9e \u2713\n"
)
BASE_ARGUMENTS = {"description": "Verify slice 1", "subagent_type": "supercook-verifier", "prompt": "supercook-role: standard\nhi"}
VALID_ENVELOPE = {"namespace": "cursor", "toolName": "Task", "arguments": {**BASE_ARGUMENTS, "model": "claude-opus-5-5-high"}}
PR_148_SHAPE = {"namespace": "cursor", "toolName": "Task", "description": "Implement", "subagent_type": "supercook-implementer", "prompt": "..."}
NOT_CLOUD_PHRASE = 'only valid when arguments.environment is "cloud"'


def load_validator():
    """Import the script by file path; registering in sys.modules first lets @dataclass resolve the module."""
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[MODULE_NAME]
        raise
    return module


def run_cli(cwd, *args, stdin_text=""):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], input=stdin_text, capture_output=True, text=True, encoding="utf-8", cwd=cwd, timeout=10,
    )


class ValidatorTestCase(unittest.TestCase):
    def setUp(self):
        if not SCRIPT.is_file():
            self.fail(f"validator script not found: {SCRIPT}")
        self.validator = load_validator()

    def assert_reported(self, lines, path, fragment):
        """Some line is `<path>: <reason>` with the stable fragment in the reason."""
        matches = [line for line in lines if line.startswith(f"{path}: ") and fragment in line]
        self.assertTrue(matches, f"no line for {path!r} containing {fragment!r} in {lines!r}")

    def assert_rejected(self, done, path, fragment):
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertEqual(done.stdout, "")
        self.assert_reported(done.stderr.splitlines(), path, fragment)

    def assert_accepted(self, done):
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "ok")

    def build(self, cwd, *flags):
        done = run_cli(cwd, "task", "--description", "Verify slice 1", "--subagent-type", "supercook-verifier", *flags)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(done.stdout.splitlines()), 1, done.stdout)
        self.assertTrue(done.stdout.isascii(), done.stdout)
        return done.stdout, json.loads(done.stdout)


class TaskEnvelopeTests(ValidatorTestCase):
    def test_valid_envelope_and_bare_arguments_are_accepted(self):
        payloads = {
            "envelope with model": VALID_ENVELOPE,
            "bare arguments": BASE_ARGUMENTS,
            "cloud with every optional field": {
                **BASE_ARGUMENTS, "environment": "cloud", "cloud_base_branch": "supercook/x",
                "run_in_background": True, "file_attachments": ["notes.md"],
            },
            "resume with interrupt and no model": {**BASE_ARGUMENTS, "resume": "agent-123", "interrupt": False},
        }
        for name, payload in payloads.items():
            with self.subTest(name):
                self.assertEqual(self.validator.validate_task_payload(payload), [])

    def test_pr_148_top_level_shape_is_rejected_naming_arguments_prompt(self):
        errors = self.validator.validate_task_payload(PR_148_SHAPE)
        self.assert_reported(errors, "arguments", "missing required object")
        self.assert_reported(errors, "arguments.prompt", "missing required field")
        for field in ("prompt", "description", "subagent_type"):
            self.assert_reported(errors, field, "Task field at top level")
        with tempfile.TemporaryDirectory() as temp:
            done = run_cli(temp, "task", stdin_text=json.dumps(PR_148_SHAPE))
        self.assert_rejected(done, "arguments.prompt", "missing required field")
        self.assert_reported(done.stderr.splitlines(), "prompt", "Task field at top level")

    def test_envelope_missing_namespace_or_tool_name_is_rejected(self):
        cases = {
            "only arguments": ({"arguments": VALID_ENVELOPE["arguments"]}, ("namespace", "toolName")),
            "missing namespace": ({key: value for key, value in VALID_ENVELOPE.items() if key != "namespace"}, ("namespace",)),
            "missing toolName": ({key: value for key, value in VALID_ENVELOPE.items() if key != "toolName"}, ("toolName",)),
        }
        for name, (envelope, missing_keys) in cases.items():
            with self.subTest(name):
                errors = self.validator.validate_task_payload(envelope)
                for key in missing_keys:
                    self.assert_reported(errors, key, "missing required field")
        with tempfile.TemporaryDirectory() as temp:
            done = run_cli(temp, "task", stdin_text=json.dumps({"arguments": VALID_ENVELOPE["arguments"]}))
        self.assert_rejected(done, "namespace", "missing required field")
        self.assert_reported(done.stderr.splitlines(), "toolName", "missing required field")

    def test_bare_arguments_missing_prompt_is_rejected(self):
        arguments = {key: value for key, value in BASE_ARGUMENTS.items() if key != "prompt"}
        errors = self.validator.validate_task_payload(arguments)
        self.assertEqual(len(errors), 1, errors)
        self.assert_reported(errors, "arguments.prompt", "missing required field")

    def test_wrong_types_empty_strings_bad_environment_and_unknown_keys_are_reported_one_per_line(self):
        envelope = {
            "namespace": "Cursor", "toolName": "task",
            "arguments": {
                "description": "", "subagent_type": 5, "prompt": "  \n\t",
                "run_in_background": "true", "interrupt": 1, "file_attachments": ["notes.md", ""],
                "environment": "remote", "subagentType": "supercook-verifier",
            },
        }
        expected = [
            ("namespace", 'must be "cursor"'),
            ("toolName", 'must be "Task"'),
            ("arguments.description", "must be a non-empty string"),
            ("arguments.subagent_type", "must be a non-empty string"),
            ("arguments.prompt", "must be a non-empty string"),
            ("arguments.run_in_background", "must be a boolean"),
            ("arguments.interrupt", "must be a boolean"),
            ("arguments.file_attachments", "must be a list of non-empty strings"),
            ("arguments.environment", 'must be "local" or "cloud"'),
            ("arguments.subagentType", "unknown field"),
        ]
        errors = self.validator.validate_task_payload(envelope)
        self.assertEqual(len(errors), len(expected), errors)
        self.assertFalse([line for line in errors if "\n" in line], errors)
        for path, fragment in expected:
            self.assert_reported(errors, path, fragment)

    def test_cloud_base_branch_without_cloud_environment_is_rejected(self):
        for name, extra in {"no environment": {}, "local environment": {"environment": "local"}}.items():
            with self.subTest(name):
                arguments = {**BASE_ARGUMENTS, "cloud_base_branch": "supercook/x", **extra}
                errors = self.validator.validate_task_payload(arguments)
                self.assert_reported(errors, "arguments.cloud_base_branch", NOT_CLOUD_PHRASE)
                with tempfile.TemporaryDirectory() as temp:
                    done = run_cli(temp, "task", stdin_text=json.dumps({**VALID_ENVELOPE, "arguments": arguments}))
                self.assert_rejected(done, "arguments.cloud_base_branch", NOT_CLOUD_PHRASE)

    def test_model_with_resume_is_rejected(self):
        errors = self.validator.validate_task_payload({**BASE_ARGUMENTS, "model": "claude-opus-5-5-high", "resume": "agent-123"})
        self.assert_reported(errors, "arguments.model", "must not be set together with arguments.resume")


class CreateAgentTests(ValidatorTestCase):
    def test_top_level_fields_are_accepted(self):
        payload = {**BASE_ARGUMENTS, "model": "claude-opus-5-5-high"}
        self.assertEqual(self.validator.validate_create_agent(payload), [])
        with tempfile.TemporaryDirectory() as temp:
            self.assert_accepted(run_cli(temp, "create-agent", stdin_text=json.dumps(payload)))

    def test_fields_nested_under_arguments_are_rejected(self):
        nested = {"prompt": "supercook-role: standard\nhi", "subagent_type": "supercook-verifier"}
        payloads = {"only nested": {"arguments": nested}, "nested beside top level": {**BASE_ARGUMENTS, "arguments": nested}}
        for name, payload in payloads.items():
            with self.subTest(name):
                errors = self.validator.validate_create_agent(payload)
                self.assert_reported(errors, "arguments.prompt", "CreateAgent field nested under arguments")
                self.assert_reported(errors, "arguments.subagent_type", "CreateAgent field nested under arguments")
                with tempfile.TemporaryDirectory() as temp:
                    done = run_cli(temp, "create-agent", stdin_text=json.dumps(payload))
                self.assert_rejected(done, "arguments.prompt", "CreateAgent field nested under arguments")


class CliTests(ValidatorTestCase):
    def test_local_parent_builds_verifier_envelope_with_prompt_file_content_inlined(self):
        with tempfile.TemporaryDirectory() as temp:
            prompt_path = Path(temp).resolve() / "verify-verifier.md"
            prompt_path.write_bytes(VERIFIER_PROMPT.encode("utf-8"))
            _, envelope = self.build(temp, "--prompt-file", str(prompt_path), "--model", "claude-opus-5-5-high")
        self.assertEqual(envelope["arguments"]["prompt"], VERIFIER_PROMPT)
        self.assertNotEqual(envelope["arguments"]["prompt"], str(prompt_path))
        self.assertEqual(envelope, {
            "namespace": "cursor", "toolName": "Task",
            "arguments": {
                "description": "Verify slice 1", "subagent_type": "supercook-verifier",
                "prompt": VERIFIER_PROMPT, "model": "claude-opus-5-5-high",
            },
        })

    def test_cloud_parent_builds_cloud_envelope_with_base_branch_that_round_trips(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "prompt.md").write_bytes(VERIFIER_PROMPT.encode("utf-8"))
            raw, envelope = self.build(
                temp, "--prompt-file", "prompt.md", "--environment", "cloud", "--cloud-base-branch", "supercook/x", "--run-in-background",
            )
            round_trip = run_cli(temp, "task", stdin_text=raw)
        arguments = envelope["arguments"]
        self.assertEqual((arguments["environment"], arguments["cloud_base_branch"]), ("cloud", "supercook/x"))
        self.assertIs(arguments["run_in_background"], True)
        self.assertEqual(arguments["prompt"], VERIFIER_PROMPT)
        self.assert_accepted(round_trip)

    def test_builder_rejects_cloud_base_branch_without_cloud_environment(self):
        for name, extra in {"no environment": (), "local environment": ("--environment", "local")}.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as temp:
                Path(temp, "prompt.md").write_bytes(VERIFIER_PROMPT.encode("utf-8"))
                done = run_cli(
                    temp, "task", "--description", "Verify", "--subagent-type", "supercook-verifier",
                    "--prompt-file", "prompt.md", "--cloud-base-branch", "supercook/x", *extra,
                )
                self.assert_rejected(done, "arguments.cloud_base_branch", NOT_CLOUD_PHRASE)

    def test_invalid_json_on_stdin_is_rejected(self):
        cases = {"truncated JSON": ('{"prompt": "unterminated', "invalid JSON"), "JSON array": ("[1, 2]", "expected a JSON object")}
        for subcommand in ("task", "create-agent"):
            for name, (stdin_text, fragment) in cases.items():
                with self.subTest(f"{subcommand}: {name}"), tempfile.TemporaryDirectory() as temp:
                    self.assert_rejected(run_cli(temp, subcommand, stdin_text=stdin_text), "stdin", fragment)

    def test_empty_or_missing_prompt_file_is_rejected(self):
        cases = {"empty file": ("", "file is empty"), "whitespace only": ("  \n\t\n", "file is empty"), "missing file": (None, "file not found: missing.md")}
        for name, (content, fragment) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as temp:
                if content is not None:
                    Path(temp, "missing.md").write_text(content, encoding="utf-8")
                done = run_cli(temp, "task", "--description", "Verify", "--subagent-type", "supercook-verifier", "--prompt-file", "missing.md")
                self.assert_rejected(done, "--prompt-file", fragment)

    def test_cli_runs_from_a_different_cwd_than_the_repo_root(self):
        with tempfile.TemporaryDirectory() as temp:
            cwd = Path(temp).resolve()
            self.assertNotIn(SCRIPT.parents[1], (cwd, *cwd.parents))
            (cwd / "prompts").mkdir()
            (cwd / "prompts" / "verify-verifier.md").write_bytes(VERIFIER_PROMPT.encode("utf-8"))
            raw, envelope = self.build(cwd, "--prompt-file", "prompts/verify-verifier.md")
            self.assertEqual(envelope["arguments"]["prompt"], VERIFIER_PROMPT)
            self.assert_accepted(run_cli(cwd, "task", stdin_text=raw))
            self.assert_accepted(run_cli(cwd, "create-agent", stdin_text=json.dumps(envelope["arguments"])))


if __name__ == "__main__":
    unittest.main()
