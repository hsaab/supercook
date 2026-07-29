# Playbook: open-pr

Work already exists in the tree. Turn it into a reviewable PR.

## Steps

Copy these into the ledger verbatim.

```
- [ ] read the full diff and understand every change before writing anything
- [ ] confirm the suite passes, or report exactly what does not
- [ ] size the diff: reviewable and raw
- [ ] split into coherent PRs if it is oversized
- [ ] write the PR body from the diff, in plain language
- [ ] hand off to babysit or merge-pr as asked
```

## Phases

| Phase | Runs? |
|---|---|
| 0 intake | yes, lightweight, no worktree since the work is already here |
| 1 assess | yes, mainly to confirm this is the right track |
| 2 recon | only enough to understand unfamiliar changed files |
| 3 design doc | no |
| 4 plan | no |
| 5 test-first | no, though a missing test for new behavior gets reported |
| 6 implement | no |
| 7 verify | yes, the diff still gets checked and the suite still gets run |
| 8 deliver | yes, this is the whole job |

## Understand the diff before describing it

Read everything: `git diff`, `git log`, and the files themselves where the diff is not self-explanatory. You are about to write the explanation a reviewer trusts, so a change you do not understand is a change you cannot describe.

Anything you genuinely cannot explain gets asked about rather than guessed at. One question naming the specific hunk is cheap. A confident wrong PR body is expensive.

## Verify before opening

The work not being yours does not exempt it from the gate. Run the suite and report honestly.

Failing tests before you touched anything are worth reporting rather than fixing: they may be why the work is unfinished. Say which tests fail and why, then ask whether to fix them in this PR or note them.

Missing tests for new behavior also get reported. Offer to add them, but do not silently expand the diff.

## Sizing and splitting

This is the track where `/split-to-prs` earns its place, because the work arrived without a slice budget.

```bash
git diff --numstat "$(git merge-base HEAD "$BASE")"
```

Report both totals: reviewable (human-authored, excluding lockfiles, generated, vendored, snapshots) and raw. Past about 500 reviewable lines, split.

Carve along the commit boundaries that already exist when they are clean. When history is one big commit, carve along dependency order instead: data shape, then logic, then wiring. Each PR must leave the default branch working.

Splitting someone else's uncommitted work is a reversible write that can lose changes if done carelessly. Snapshot first, never discard, and confirm the split plan before moving anything.

## The PR body

Same three sections as any other delivery, from [../pipeline/delivery.md](../pipeline/delivery.md): why we did this, what the outcome is, operational tasks.

Write it from the diff, in the house style: name files and functions, connect each change to real consequence. Where you had to ask the author what something did, use their answer rather than paraphrasing it into vagueness.
