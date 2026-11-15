# Test first

Tests define done, and they are committed before the code that satisfies them. `supercook-test-designer` owns every test edit for the whole run, so the implementer cannot bend a test until it passes.

## The brief

The slice, the journeys it serves from `plan.md`, the test command, the repo's test conventions from recon, and the mode:

- `red-first`: the default. New tests fail on their own assertions because the behavior is missing.
- `characterization`: refactor, and retrospective UI tests on open-pr. Tests pin what the code does today and pass against it; the designer reports pass or a gap honestly and never claims red.

## After it returns

Run the test-designer check in [workers.md](workers.md#checks-after-each-return): only test paths changed, and on red-first `guard red` confirms the failures with the designer's temporary stub applied. The stub is how a test reaches its real assertion instead of dying at an import error; the designer saves it as `red-stub.patch` in the run folder and deletes it, so the commit holds tests only. Then commit that slice's tests alone and record the SHA on the slice's row as `tests <sha>`. The `red-evidence` lines go into the PR's Evidence section.

## Rules

- **Commit per slice, not all at once.** Each slice's tests land at the start of that slice, so every PR carries its own red-to-green story and merges green.
- **Repos that require every commit green**: keep the red evidence in the ledger and the PR body, then squash the test commit into the implementation commit before pushing.
- **No test runner**: the designer returns an executable recipe (setup, assertions, expected output, cleanup). Write it to `verification-<slice>.md` in the run folder, record its path in `plan.md` and its hash from `guard recipe <file>` in the ledger. Ordered prose that cannot run is not a recipe.
- **Trivial work that needs a test**: launch the test designer before the implementer; neither you nor the implementer edits tests.
- **Contract-level UI**: run the anchor check in [ui.md](ui.md#tests-and-the-anchor-check) before implementation starts.
