# Refactor

Same behavior, better structure. If behavior changes, this is not a refactor.

## Steps

Copy these into the ledger verbatim. The reason after a worker is why the step is not yours.

```
- [ ] map the current shape: supercook-explorer (understanding it is the prerequisite)
- [ ] plan small slices, each green on its own: supercook-planner, per references/plan.md
- [ ] pin current behavior before moving anything: supercook-test-designer in characterization mode, per references/test-first.md (it owns the tests, so the move cannot quietly rewrite them)
- [ ] those tests pass against the code as it is today (yours: run them and quote the output)
- [ ] move structure in small steps, suite green after each: supercook-implementer, one launch per slice, per references/implement.md (you check each diff for a behavior change)
- [ ] behavior is unchanged: supercook-verifier, a fresh launch, per references/verify.md (it did not do the move)
- [ ] say concretely what got easier, then open the PR (yours), per references/deliver.md
```

## Rules

- Characterization tests capture what the code does today, odd parts included (`existing: an expired token passes on the first request and fails on the second`). Something may depend on the oddity; fixing it is a separate PR.
- A characterization test that fails before you start means there is a bug. Reroute to bugfix.
- Needing to change what the code does means stop: log it, tell the user, reroute to feature. A behavior change hidden in a refactor is the most dangerous diff shape, because reviewers read refactors quickly.
- When layout is in scope, rendered behavior is part of the characterization, per [../references/ui.md](../references/ui.md).
- Ship only if the next reader's load drops. "Cleaner" is not concrete; what got shorter, stopped being duplicated, or stopped being surprising? If you cannot say, revert it as churn.

**Reply:** what got easier to read or change, naming the files, and the PR link.
