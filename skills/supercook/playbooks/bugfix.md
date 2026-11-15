# Bugfix

Something is broken. Reproduce it, find the actual cause, and fix the smallest thing that resolves it.

## Steps

Copy these into the ledger verbatim. The reason after a worker is why the step is not yours.

```
- [ ] reproduce it and put the real failure output in the ledger (yours: every brief starts from it)
- [ ] find the root cause with evidence: supercook-explorer scoped to the failing path (you name the cause from its pointers)
- [ ] plan the fix, usually one slice: supercook-planner, per references/plan.md
- [ ] a failing repro test lands before the fix: supercook-test-designer, per references/test-first.md (so the fix is provably what turned it green)
- [ ] fix the smallest thing the evidence justifies: supercook-implementer, per references/implement.md (you check its diff against the proven cause)
- [ ] the repro and the full suite pass: supercook-verifier, a fresh launch, per references/verify.md (it did not write the fix)
- [ ] note the same mistake elsewhere for the PR body, without fixing it (yours)
- [ ] open the PR (yours), per references/deliver.md
```

## Rules

- A bug you cannot reproduce is an investigation. Say so and reroute.
- The symptom is where it surfaced; the cause is where it went wrong. A guard against a null in the file that threw is not a fix if the null should never have got there.
- A hypothesis becomes the cause when you can point at the line and explain why it produces exactly this failure. `git log -p` on the path helps.
- Name the repro test after the failure a user would recognize: `webhook with no retry record returns 200 instead of throwing`.
- For a visual bug the reproduction is the rendered route in the failing state, per [../references/ui.md](../references/ui.md). A green test on the same broken page is not fixed.

**Reply:** the cause (file, function, why it produced this symptom), the fix, and the PR link. The PR's "why" is the story of the bug.
