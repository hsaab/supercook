# Workers

Agent files live at `<plugin root>/agents/supercook-<role>.md`. Each holds that worker's procedure, budget, done-when, and return shape; the brief supplies the rest. On a host that mirrored only the skill, look in `~/.cursor/agents/`. If no file can be found, launch anyway with the brief below as the prompt and log `agent file missing`; a missing file never moves a role to you.

## Roster

| Worker | Roster key | Writes | Brief |
|---|---|---|---|
| `supercook-explorer` | explorer | nothing | a question list for one area, not a topic. The first, broad launch also asks for the test command and test paths |
| `supercook-planner` | standard | `plan.md` | task, tier, track, recon pointers, design doc, slice budget; `mode: supplied-plan` on implement-plan |
| `supercook-arena-runner` | arena-a, arena-b, arena-c | its candidate file | the same brief for all three; only the model and the candidate file name differ |
| `supercook-plan-judge` | plan-judge | `plan.md` | the three candidate paths, recon pointers, slice budget |
| `supercook-test-designer` | standard | test files | slice, journeys, test command, conventions, `mode: red-first` or `characterization` |
| `supercook-implementer` | implementer, or review-implementer on the review track | scoped source, never tests | explicit file list, data shape, the failing tests, the test command |
| `supercook-verifier` | standard | nothing | the contract per [verify.md](verify.md#the-contract-it-checks-against) (`plan.md`, the task text and `done:` on trivial, or the `open-pr scope` baseline), the diff range, the test command; nothing about how the code was built |

Every brief names the run folder (where `plan.md`, `user-plan.md`, `acceptance.md`, and `design-doc.md` live), the roster key, and the plain-language rule for its return. UI work adds only the contract entries and evidence that role owns, per [ui.md](ui.md). The review track also launches host reviewers (bugbot, security-review, both thermo reviewers) on the `reviewer` key; see [review.md](review.md).

## Checks after each return

A boundary in a prompt is a request; these checks are the control. `guard` below means `python3 <plugin root>/scripts/guard.py`, run from the working tree. It exits 0 on a pass, 1 on a violation it prints, and 2 when it could not run (a bad argument or ref, a git error, a missing file, a test command that would not start or timed out); a 2 is never a pass.

| After | Check |
|---|---|
| any worker | Read its diff yourself. Log the agent id and the model actually used. |
| explorer | Every question has a `file:line` or "not found". The broad launch's test command and test paths cite evidence (scripts, CI, runner config); record both in the header. |
| planner, judge | Every slice has a scope list, a named verification, and an estimate under 500 or an `exception:`. Every `acceptance.md` criterion maps to a slice and a check. Supplied-plan mode also has `## Changes from your plan`, each line traceable to recon or the user's plan. |
| test-designer | `guard scope --allow <test globs> --since <sha before launch>` passes. On red-first, `guard red --cmd '<test command>' --expect <red-evidence test names> --tests <test globs>` confirms red; when its `stub-patch` names a file, add `--patch <run folder>/red-stub.patch --stub <stub path>`, and each stub path must be one of the slice's files. The expected names are its journey assertions, not setup lines. Then commit the tests alone. |
| implementer | `guard scope --allow <slice files> --tests <test globs> --since <tests sha> --fix`, and `guard recipe check <file> <recorded sha>` when a recipe replaced tests. Both pass before you commit. |
| verifier | Fresh test output is quoted, one line per plan row and per acceptance criterion, and `verdict: pass` before the step closes. A verdict reasoned from the diff alone gets a relaunch. |

`--cmd` is the test command you recorded at recon; take it from your own record, not from a ledger a worker could have edited. `--fix` restores an edited test, committed or not, from `--since` and deletes an added one; log each. It only names out-of-scope source and never restores it. A test that is genuinely wrong goes to the test designer, never the implementer. A planner that needed to explore means recon was too thin: launch another explorer for the gap.

## Other hosts

On a host without `Task`, use the spawn tool it lists, name the worker `supercook-<role>`, and brief it the same way. Through `CallDynamicTool` (`namespace: cursor`, `toolName: Task`) the launch fields go under `arguments`. Prefer a local, same-checkout worker so it can read `.supercook/`. A worker on a separate VM gets its agent file body and every input inline in the prompt and pushes its commits to the run branch; fetch them and run the same check.

## Solo mode

Only when no spawn tool is listed (`spawn: none`), run each worker step yourself from that role's agent file, in order, marking it `inline (spawn none)`. A failed launch is never a reason: fix the brief or the model and launch again. The steps, tier skips, and checks stay the same; the guarantees come from files and git instead of a second agent.

- No product file changes until the ledger exists and the verdict is logged, and no test file until `plan.md` exists or the plan step is a tier skip.
- Each step leaves its file: `recon.md`, then `plan.md` reviewed once against the judge's criteria with a `## Strongest objection` section, then the tests committed alone, then `verify.md` written after the slice is committed from a fresh `git diff` and test run.
- The arena does not run; log `arena: n/a (solo)`.
- The PR's Evidence section says "built in solo mode, no independent review: verify was a self-audit".
