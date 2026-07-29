# Playbook: bugfix

Something is broken. Reproduce it, find the actual cause, fix the smallest thing that resolves it.

## Steps

Copy these into the ledger verbatim.

```
- [ ] reproduce the bug and capture the real failure output
- [ ] find the root cause with evidence, not a guess
- [ ] write a failing test that reproduces it
- [ ] fix the smallest thing the evidence justifies
- [ ] confirm the repro test passes and the rest of the suite still does
- [ ] check for the same mistake elsewhere, report rather than fix
```

## Phases

This table describes standard and complex tier. A trivial bugfix collapses to implement plus verify, per the precedence rule in `SKILL.md`.

| Phase | Runs? |
|---|---|
| 0 intake | yes |
| 1 assess | yes |
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

## Root cause, with evidence

The symptom is where it surfaced. The cause is where it went wrong. Those are usually different files.

Follow the evidence: read the stack trace properly, check what changed recently in that path with `git log -p`, and confirm your hypothesis before acting on it. A hypothesis becomes a cause when you can point at the line and explain why it produces exactly this failure.

Guarding against a null in the file that threw is not a fix if the null should never have got there. Ask where the bad value came from.

## The failing repro test lands first

The repro test goes in history before the fix, so the fix is provably what turned it green. That ordering is also what stops the same bug coming back later.

Name the test after the failure a user would recognize:

```
webhook with no retry record returns 200 instead of throwing
```

## Smallest fix the evidence justifies

Fix the cause you proved, not everything nearby that looks fragile. The diff should be small enough that a reviewer can see the causal link between the change and the bug.

Same class of mistake elsewhere in the codebase goes in the PR body as a note, and becomes a follow-up. It does not go in this diff.

## PR body

The `why` section is the story of the bug: what was wrong, why it produced this symptom, what a user experienced. The plain-language rule does its best work here.

> `handleWebhook` in `src/api/webhook.ts` read `retryCount` off a variable the queue rewrite deleted, so every inbound webhook threw on the first line and the sender saw a 500. It now reads the attempt count off the queue record, which is where that state has lived since the rewrite.
