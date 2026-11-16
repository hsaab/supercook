# Refactor

Same behavior, better structure. If behavior changes, this is not a refactor.

## Steps

Copy these into the ledger verbatim, with the slice block once per slice per references/ledger.md. The reason after a worker is why the step is not yours.

```
- [ ] map the current shape: supercook-explorer (understanding it is the prerequisite)
- [ ] plan small slices, each green on its own: supercook-planner, per references/plan.md
- [ ] each slice in plan order, closed before the next starts (yours)
  - [ ] slice <n> behavior pinned before anything moves: supercook-test-designer in characterization mode, per references/test-first.md (it owns the tests, so the move cannot quietly rewrite them)
  - [ ] slice <n> pins pass against the code as it is today (yours: run them and quote the output)
  - [ ] slice <n> structure moves in small steps, suite green after each: supercook-implementer, per references/implement.md (you check its diff for a behavior change)
  - [ ] slice <n> behavior is unchanged: supercook-verifier, a fresh launch, per references/verify.md (it did not do the move)
  - [ ] slice <n> PR opens, saying concretely what got easier (yours), per references/deliver.md
- [ ] behavior is unchanged across every slice: supercook-verifier, a fresh launch, per references/verify.md
```

## Rules

- Characterization tests capture what the code does today, odd parts included (`existing: an expired token passes on the first request and fails on the second`). Something may depend on the oddity; fixing it is a separate PR.
- A characterization test that fails before you start means there is a bug. Reroute to bugfix.
- Needing to change what the code does means stop: log it, tell the user, reroute to feature. A behavior change hidden in a refactor is the most dangerous diff shape, because reviewers read refactors quickly.
- When layout is in scope, rendered behavior is part of the characterization, per [../references/ui.md](../references/ui.md).
- Ship only if the next reader's load drops. "Cleaner" is not concrete; what got shorter, stopped being duplicated, or stopped being surprising? If you cannot say, revert it as churn.

**Reply:** what got easier to read or change, naming the files, and the PR link.
