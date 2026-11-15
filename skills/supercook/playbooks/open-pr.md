# Open PR

Work already exists in the tree. Turn it into a reviewable PR. No tier sends this track through planning or implementation, but the diff is still verified.

## Steps

Copy these into the ledger verbatim. The reason after a worker is why the step is not yours.

```
- [ ] read the full diff, then log `open-pr scope`: the task, base and head SHAs, and every changed or untracked path with a one-line purpose (yours: you write the PR body)
- [ ] the recorded tests pass, or exactly what fails is reported: supercook-verifier against the open-pr scope, per references/verify.md (fresh context judges the diff, not the story about it)
- [ ] size it with `guard lines` and split it along its commits if over budget (yours), per references/deliver.md
- [ ] write the PR body from the diff and open it (yours), per references/deliver.md
```

## Rules

- A change you cannot explain gets one question naming the hunk, not a guess.
- Tests failing before you touched anything are reported, not fixed: they may be why the work is unfinished. Ask whether to fix them here.
- Missing tests for new behavior are reported and offered, never silently added. Contract-level UI is the exception: its structure tests come from `supercook-test-designer` in characterization mode, per [../references/ui.md](../references/ui.md).
- Check the raw count too: work that arrived without a budget is where a committed `dist/` or regenerated lockfile shows up.
- Splitting someone else's uncommitted work can lose it. Snapshot first, never discard, and confirm the split before moving anything.
- The Evidence section says the verification was retrospective; there is no red-first block.

**Reply:** what the PR does, naming the files, what the tests showed, and the PR link.
