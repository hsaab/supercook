# Feature

New or changed behavior.

## Steps

Copy these into the ledger verbatim, with the slice block once per slice per references/ledger.md. The reason after a worker is why the step is not yours.

```
- [ ] map the code the feature touches: supercook-explorer, a broad launch then one per area in parallel (its clean context reads the repo so yours holds the task)
- [ ] design doc, big-change only (yours, with the user), per references/design-doc.md
- [ ] plan.md names the data shape and the user journeys: supercook-planner, or three supercook-arena-runner launches then supercook-plan-judge on complex, per references/plan.md (you check the plan, so you do not write it)
- [ ] each slice in plan order, closed before the next starts (yours)
  - [ ] slice <n> journey tests land red before the code: supercook-test-designer, per references/test-first.md (it owns every test edit, so the implementer cannot bend them)
  - [ ] slice <n> code: supercook-implementer, per references/implement.md (you check and commit its diff)
  - [ ] slice <n> matches its plan rows: supercook-verifier, a fresh launch, per references/verify.md (it did not write the code)
  - [ ] slice <n> PR opens (yours), per references/deliver.md
- [ ] the feature works end to end across every slice: supercook-verifier, a fresh launch, per references/verify.md
```

## Rules

- Settle the data shape (types, schema, payload, ownership) in `plan.md` before any logic, so the implementer does not invent one. The first slice is usually types and config.
- Tests come from journeys: who uses this and what they are trying to do (`a returning user hits the rate limit and sees a clear error`), then the realistic variations. No tests for private helpers or unreachable input.
- Reuse what exists and match its conventions. Two implementations of one idea is what makes a codebase hard to change.
- The refactor or unrelated bug you noticed goes in `plan.md`'s out-of-scope section and the PR body, not the diff.
- "Tests pass" is weaker than what you saw on the real path: "101 calls in a minute came back 429 with retry-after set". Put the observation in the PR.

**Reply:** what now works, the files that make it work, and the PR links.
