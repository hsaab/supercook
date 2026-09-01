# Playbook: open-pr

Work already exists in the tree. Turn it into a reviewable PR.

## Steps

Copy these into the ledger verbatim.

```
- [ ] read the full diff and understand every change before writing anything
- [ ] inventory the preexisting diff as the verifier's scope baseline
- [ ] supplied UI design is reconstructed as a ledger contract
- [ ] confirm the recorded tests or recipe pass, or report exactly what does not
- [ ] changed UI routes pass rendered smoke before the PR opens
- [ ] size the diff: reviewable and raw
- [ ] split into coherent PRs if it is oversized
- [ ] write the PR body from the diff, in plain language
- [ ] hand off to babysit, or continue into phase 9 merge, only if asked
```

## Phases

This track skips planning and source implementation entirely, but it is not delivery alone: the diff is still verified and its recorded tests or recipe still run. This routing wins at every tier, including trivial. `open-pr` never enters phase 6 just because tier collapse normally says implement plus verify.

| Phase | Runs? |
|---|---|
| 0 intake | yes, lightweight, no worktree since the work is already here |
| 1 assess | yes, mainly to confirm this is the right track |
| 2 recon | only enough to understand unfamiliar changed files |
| 3 design doc | no |
| 4 plan | no |
| 5 test-first | only in retrospective mode for a supplied UI contract whose structural verification is missing |
| 6 implement | no |
| 7 verify | yes, the diff and recorded verification still run |
| 8 deliver | yes, this is the whole job |
| 9 merge | only when the user asked for the PR merged too |

## Understand the diff before describing it

Read everything: `git diff`, `git log`, and the files themselves where the diff is not self-explanatory. You are about to write the explanation a reviewer trusts, so a change you do not understand is a change you cannot describe.

Anything you genuinely cannot explain gets asked about rather than guessed at. One question naming the specific hunk is cheap. A confident wrong PR body is expensive.

Before the test designer or any other allowed write, record `open-pr scope` in the
ledger: the user's task, current head SHA, every preexisting changed and untracked
path from the target-base diff and worktree, and a one-line purpose for each diff
unit. Deliberate retrospective test files are appended to that inventory when they
land. The verifier treats this baseline, not nonexistent plan slices, as the
authorized scope.

## Verify before opening

The work not being yours does not exempt it from the gate. Run the recorded tests
or recipe and report honestly.

Failing tests before you touched anything are worth reporting rather than fixing: they may be why the work is unfinished. Say which tests fail and why, then ask whether to fix them in this PR or note them.

Missing tests for new behavior also get reported. Offer to add them, but do not silently expand the diff.

For contract-level UI work, missing structural assertions are not optional PR notes.
Resolve the supplied design, reconstruct the `UI source of truth` entry in the
ledger using [../pipeline/ui.md](../pipeline/ui.md), and send its obligations to the
test designer in retrospective mode. The tests or recipe run after the existing
source, so they report pass or gap rather than claiming a red-first failure. Record
that this is retrospective evidence.

Pre-edit design evidence is not required because the work already exists. The
parent still compares the diff to the contract, the verifier receives the ledger
contract in place of `plan.md`, and every changed route must pass rendered smoke
before delivery. Wrong order, missing regions, or failed smoke stops the PR and
requires the user to approve and record a material deviation or authorize a
source-fix run. An approved deviation updates the ledger contract and its
verification before smoke runs again.

## Sizing and splitting

This is the track where `/split-to-prs` earns its place, because the work arrived without a slice budget.

Take both counts with the commands in [../pipeline/implementation.md](../pipeline/implementation.md#line-accounting), and report both: reviewable (human-authored) and raw (what the reviewer sees). Past about 500 reviewable lines, split.

Check the raw number carefully on this track. Work that arrived without a budget is where a committed `dist/` directory or a regenerated lockfile turns up, and that is worth telling the user about even though it does not count against the budget.

Carve along the commit boundaries that already exist when they are clean. When history is one big commit, carve along dependency order instead: data shape, then logic, then wiring. Each PR must leave the default branch working.

Splitting someone else's uncommitted work is a reversible write that can lose changes if done carelessly. Snapshot first, never discard, and confirm the split plan before moving anything.

## The PR body

Same three sections as any other delivery, from [../pipeline/delivery.md](../pipeline/delivery.md): why we did this, what the outcome is, operational tasks.

Write it from the diff, in the house style: name files and functions, connect each change to real consequence. Where you had to ask the author what something did, use their answer rather than paraphrasing it into vagueness.
