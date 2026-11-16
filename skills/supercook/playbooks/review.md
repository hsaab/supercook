# Review

Slice PRs exist. Run the external reviewers on each one, fix the real findings, and merge only when the ask said so. The ask fixes the mode: `review` stops at healthy open PRs; `review and merge` merges each PR after its own review. Record `mode:` in the ledger header. A clean review never becomes a merge.

Resolve the targets before any launch: the named PRs, or the current branch's PR and every open PR stacked on it. Record them bottom-up with each base branch. Inside a live run, reuse its ledger.

## Steps

Copy these in verbatim, one nested block per PR, and finish one PR before opening the next:

```
- [ ] resolve the targets and record them bottom-up with each base (yours)
- [ ] for each PR, bottom-up:
  - [ ] check out the branch and resolve bugbot and security-review to hosted, local, or pending per references/review.md
  - [ ] launch both thermo reviewers and every local reviewer in one parallel batch, scoped to this PR's base; collect hosted findings
  - [ ] once all have reported, dedupe and triage; decline the rest with a reason (yours)
  - [ ] fix the in-scope findings: supercook-implementer, one launch on the review-implementer key (you check and commit its diff)
  - [ ] run the recorded tests, plus the rendered smoke when a fix touched a rendered file under a UI contract, then push; a finding fixed but never verified is not fixed
  - [ ] one confirmation pass on the reviewers whose findings were fixed; at most one more implementer launch, then stop
  - [ ] CI checks green, per references/merge.md
  - [ ] merge mode only: merge this PR per references/merge.md
  - [ ] after that merge or a fix pushed to this PR, restack its children per references/stacking.md
- [ ] report per PR: found, fixed (file and consequence), declined (with reason), left open
```

## Rules

- Bottom-up, one PR at a time. A fix on a base slice moves what every child sits on.
- Never bulk-merge a stack, and never skip to the tip because "the stack was reviewed".
- Fixes always go through the implementer launch, even one-line ones, so they run on the right model with a clean context.
- Pushing fixes and restacking run-owned branches are reversible writes. Force-pushing a branch the run does not own asks.

**Reply:** one short block per PR: findings found, fixed, declined, and left open, plus whether it merged.
