# Playbook: refactor

Same behavior, better structure. If behavior changes, this is not a refactor.

## Steps

Copy these into the ledger verbatim.

```
- [ ] pin current behavior with characterization tests before moving anything
- [ ] confirm those tests pass against the code as it is today
- [ ] move structure in small steps, suite green after each one
- [ ] behavior change discovered means stop and reroute to feature
- [ ] state what got easier, concretely, before opening the PR
```

## Phases

| Phase | Runs? |
|---|---|
| 0 intake | yes |
| 1 assess | yes |
| 2 recon | yes, understanding the current shape is the prerequisite |
| 3 design doc | only if a public interface or data shape moves |
| 4 plan | yes, small slices, each one green on its own |
| 5 test-first | yes, but characterization tests rather than new-behavior tests |
| 6 implement | yes |
| 7 verify | yes, plus explicit confirmation that behavior is unchanged |
| 8 deliver | yes |

## Characterization tests come first

A refactor without tests pinning the current behavior is not a refactor, it is a rewrite with extra confidence.

Characterization tests are different from feature tests. They do not describe what the code **should** do. They capture what it **does** today, including the parts that look wrong:

```
existing: a webhook with no retry record returns 200 with an empty body
existing: an expired token passes on the first request and fails on the second
```

Write them, run them, confirm they pass against untouched code. A characterization test that fails before you start is telling you there is a bug, which means you are on the wrong track. Stop and reroute to bugfix.

Preserve the odd behavior in the test even when it looks like a mistake. Something may depend on it. Fixing it is a separate, deliberate change with its own PR.

## Move in small steps

Each step keeps the suite green. Extract one function, move one file, collapse one duplicated block, then run the tests.

This is what makes a refactor reviewable. Ten small commits that each keep the suite green are easy to follow and easy to bisect. One enormous "restructured the module" commit is neither.

## Behavior change means stop

The moment you find yourself needing to change what the code does, this stops being a refactor.

Log it, tell the user in one line, and reroute to the feature track so the change gets tests for its new behavior and a Design Doc if it deserves one. Do not quietly ship a behavior change inside a refactor PR. That is the single most dangerous diff shape there is, because reviewers read refactors quickly.

## Only ship if reader load drops

The bar for a refactor is that the next reader has an easier time. Before opening the PR, say concretely what got better:

> `src/api/webhook.ts` went from one 180 line function with four nested conditionals to three
> named functions with the retry decision in `shouldRetry`. The retry rule is now in one place
> instead of duplicated in the handler and the queue worker.

If you cannot name the improvement in those terms, the refactor is churn. Churn costs review time and risks regressions while buying nothing. Revert it and say why.

"More idiomatic", "cleaner", and "better separation of concerns" are not concrete. What got shorter, what stopped being duplicated, what stopped being surprising?
