# Playbook: bugfix

Something is broken. Reproduce it, find the actual cause, fix the smallest thing that resolves it.

## Steps

Copy these into the ledger verbatim. A step that names a worker is that worker's launch; the reason after it is why the step is not yours.

```
- [ ] reproduce the bug and capture the real failure output (yours: you brief every worker from it)
- [ ] find the root cause with evidence, not a guess: supercook-explorer scoped to the failing path returns the pointers, and you name the cause from them
- [ ] write a failing test or executable recipe that reproduces it: supercook-test-designer (the repro lands before the fix, so the fix is provably what turned it green)
- [ ] fix the smallest thing the evidence justifies: supercook-implementer (you review its diff against the proven cause, so you do not write it)
- [ ] confirm the repro verification and the full recorded verification pass: supercook-verifier, a fresh launch (it did not write the fix)
- [ ] visual bug only: reproduce and confirm the fix on the rendered route (yours)
- [ ] check for the same mistake elsewhere, report rather than fix (yours)
```

## Phases

This table describes standard and complex tier. A trivial bugfix collapses to implement plus verify, per the precedence rule in `SKILL.md`.

| Phase | Runs? |
|---|---|
| 0 intake | yes |
| 1 assess | yes, yours |
| 2 recon | yes, scoped to the failing path |
| 3 design doc | only if the fix changes an interface or data shape |
| 4 plan | yes, usually one slice |
| 5 test-first | yes, the repro test is the suite |
| 6 implement | yes |
| 7 verify | yes |
| 8 deliver | yes |

## Reproduce first

Do not start fixing something you have not seen fail. Get the real error, the real stack trace, the real input that triggers it. Put the actual output in the ledger.

A bug you cannot reproduce is an investigation, not a bugfix. Say so and reroute.

For a visual bug, the real reproduction is the rendered route in the failing state,
not only a component test. Record the route, viewport, seed or auth state, and what
was visibly wrong. When a supplied design exists, load
[../pipeline/ui.md](../pipeline/ui.md): a hierarchy, order, geometry, interaction,
or responsive fix uses the contract gate and its structure tests.

## Root cause, with evidence

The symptom is where it surfaced. The cause is where it went wrong. Those are usually different files.

Follow the evidence: read the stack trace properly, check what changed recently in that path with `git log -p`, and confirm your hypothesis before acting on it. A hypothesis becomes a cause when you can point at the line and explain why it produces exactly this failure.

Guarding against a null in the file that threw is not a fix if the null should never have got there. Ask where the bad value came from.

## The failing repro verification lands first

The repro test, or run-folder recipe when no runner exists, lands before the fix, so
the fix is provably what turned it green. That ordering is also what stops the same
bug coming back later.

Name the test after the failure a user would recognize:

```
webhook with no retry record returns 200 instead of throwing
```

## Smallest fix the evidence justifies

Fix the cause you proved, not everything nearby that looks fragile. The diff should be small enough that a reviewer can see the causal link between the change and the bug.

Same class of mistake elsewhere in the codebase goes in the PR body as a note, and becomes a follow-up. It does not go in this diff.

Render the original route and state again after the fix. The repro test and full
suite must pass, and the visible failure must be gone. A green test with the same
broken page is not fixed.

## PR body

The `why` section is the story of the bug: what was wrong, why it produced this symptom, what a user experienced. The plain-language rule does its best work here.

> `handleWebhook` in `src/api/webhook.ts` read `retryCount` off a variable the queue rewrite deleted, so every inbound webhook threw on the first line and the sender saw a 500. It now reads the attempt count off the queue record, which is where that state has lived since the rewrite.
