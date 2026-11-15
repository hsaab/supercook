# Deliver

One PR per slice, opened as each slice closes, not one batch at the end. Dependent slices stack per [stacking.md](stacking.md).

## The PR body

This is the most-read thing the workflow produces, so plain language applies at full strength:

```markdown
## Why we did this
What was wrong or missing, in terms of the actual code and its real consequence. Name files and functions.

## What the outcome is
What now works that did not before. Name each changed file and what it does now.

## Operational tasks
- [ ] anything a human has to do: env var, migration, feature flag, rollback note

## Evidence
Red first (test commit <sha>, tests only):
- <test name>: <assertion line that failed before the code existed>

| Acceptance criterion (verbatim) | Test or check | Passing output |
|---|---|---|
| AC-1: <text> | <test or command> | <quoted passing line> |
```

> `handleWebhook` in `src/api/webhook.ts` still read a `retryCount` variable the queue rewrite deleted, so every real webhook threw before doing anything. It now reads the attempt count off the queue record.

Not: "Fixed webhook handling and improved retry logic for better reliability."

- Red-first lines come from the test designer's `red-evidence`. Open-pr runs, and trivial runs with no test designer launch, have none and say so.
- The acceptance table appears only when `acceptance.md` exists; a row without proof means the PR does not open.
- A solo run adds "Built in solo mode, no independent review: verify was a self-audit."
- A recipe that replaced tests goes in the body (or a durable link) with its hash, because the run folder does not travel.
- With a repo PR template, these sections are the minimum content fitted into its fields. Proof lives in the body or a PR comment, never in the diff.

## Before opening any PR

This check fails closed: a failure means the PR is not opened and the step that owns the gap reopens.

1. Every row above this PR's row is `[x]`, `[~]` with a valid reason, or a sanctioned `[!]`, apart from the slice step that holds it. Rows below it, later slices and the final verify, stay open.
2. `guard ledger` passes: the worker rows follow [ledger.md](ledger.md#rows) and match the launch log.
3. `guard scope --allow <slice files> --tests <test globs> --base <base>` passes, so the branch holds only scoped files and its own tests. A QA note, log, or leftover stub fails; move it to the run folder.
4. `guard lines --base <base>` is under budget, or the slice carries the cohesion exception logged at plan time. Do not mint one now; split instead.
5. Every acceptance criterion has a passing line from the verifier, and the Evidence section is filled.
6. A UI slice's rendered-smoke row is `pass`, or sanctioned-blocked with the missing evidence named in the body.

Log the result and both line counts on the deliver row. Without `gh`, push the branch (or keep the commits local), write the body to the run folder, and say where it is.

A diff that landed oversized anyway, or open-pr work that arrived oversized, splits with the built-in `/split-to-prs` flow along its commits.

## Handoff

- **Nothing more** (the default): report and stop at the open PRs.
- **Keep it healthy**: hand off to the built-in `/babysit` (comments, CI, conflicts, no merge).
- **Get it merged**: append the merge playbook's steps, only on an explicit ask. A PR that looks mergeable is not an ask.

The final reply is a few outcome sentences in the PR body's style: what changed, in which files, and what it means, plus the PR links.
