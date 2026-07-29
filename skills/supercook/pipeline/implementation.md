# Phases 5 and 6: test-first, then implement

Tests define done, and they get committed before the code that satisfies them. Then implementation happens in surgical chunks with the parent checking every one.

## Contents

- [Phase 5: test-first](#phase-5-test-first)
- [Phase 6: implement](#phase-6-implement)
- [The guards](#the-guards)
- [Line accounting](#line-accounting)
- [When a chunk goes wrong](#when-a-chunk-goes-wrong)

## Phase 5: test-first

Launch `supercook-test-designer` with the slice, its journeys from `plan.md`, the test command, and the repo's test conventions.

**Design from journeys, not from code.** Name who uses this and what they are trying to do, write those as tests with names a non-engineer could read, then add the realistic variations: bad input at a real entry point, empty state, the retry, permission denied. An edge case earns a test only when it sits on a path a user can actually reach.

**Commit per slice, not all at once.** The suite is designed once for the whole task, but each slice's tests land at the start of that slice. That way every PR carries its own red-to-green story and merges green. Committing the entire failing suite up front would leave slice 1's PR holding red tests for slices 2 and 3, and it could never merge.

Single-slice work collapses to the simple case: whole suite committed first.

**Verify the failure before moving on.** Each new test must fail because the behavior is missing, not because of a typo or a bad import. A test failing for the wrong reason sends the implementer chasing a phantom.

**Where every commit must be green.** Some repos require it. Keep the red evidence in the ledger, then squash the test commit together with the implementation commit before pushing. The discipline survives; only the history shape changes.

**Where there is no test runner.** The test designer writes an executable verification recipe into the plan instead: a script, a command sequence, or ordered manual steps. The verifier runs that. Journey thinking survives, only the assertion mechanism changes.

## Phase 6: implement

One `supercook-implementer` launch per slice, or per chunk within a slice when a slice has natural internal steps.

Each launch gets:

- **An explicit file list**, the only files it may touch.
- **The data shape**, so it does not invent one.
- **The failing tests to green**, by name.
- **The test command.**

Then, for every return, the parent does four things in this order:

1. **Run the guards** (below). Before committing, always.
2. **Read the diff yourself.** The agent's summary is a claim. Its diff is the evidence.
3. **Commit that unit**, with a message in the house style: what changed, in which file, why, and what it means.
4. **Update the ledger and the plan checkboxes**, with the running line counts.

Between launches, **re-anchor**: name the open ledger row the next action serves. Cannot name one? That is drift. Log a course-correction row and get back on an open row.

## The guards

A boundary written in a prompt is a request. These are what make it a control.

### Test integrity

Detection has to be right or the guard is theatre. `git diff --name-only` does not report an untracked file, and `git restore` cannot remove one, so an implementer that **adds** `thing.test.ts` walks straight through a diff-only check.

```bash
# BEFORE committing the chunk
git status --porcelain --untracked-files=all
```

Match every changed and every new path against the test patterns recorded in the ledger during recon:

- **Modified test**: `git restore --source=HEAD --staged --worktree -- <paths>`
- **Added test**: delete it.
- Either way: log a guard row naming the file.

Order matters. Commit first and `--source=HEAD` cheerfully restores the tampered version.

A report that a test is genuinely wrong becomes a `supercook-test-designer` amendment. Tests change only through the role that owns them, deliberately and on the record. This is the whole defense against an agent bending a test until it passes.

### Scope

Same mechanism, different match list. A changed path outside the slice's declared scope gets restored or deleted, logged, and the chunk re-delegated with a corrected scope.

## Line accounting

This is the one definition of the counts. Everywhere else refers here.

`BASE` is the branch this slice will target: the default branch for an independent slice, or the previous slice's branch for a stacked one.

```bash
BASE=$(git merge-base HEAD origin/<base-branch>)

# Raw: everything the reviewer will see.
git diff --numstat "$BASE" | awk '{t+=$1+$2} END {print t+0}'

# Reviewable: human-authored only. This is what the budget applies to.
git diff --numstat "$BASE" -- \
  ':!*.lock' ':!*lock.yaml' ':!*lock.json' ':!*.snap' ':!vendor' ':!*generated*' \
  | awk '{t+=$1+$2} END {print t+0}'
```

**The exclusions must be spelled out or they do nothing.** A bare `git diff --numstat` gives the raw count only, so the two totals come out identical and the budget silently stops meaning anything. Two syntax traps, both easy to hit:

- `:!<pattern>` (or the long form `:(exclude)<pattern>`) works. A `**/`-prefixed pattern like `':(exclude)**/package-lock.json'` silently matches nothing at the repo root, so the file stays in the count and the filter looks like it ran.
- Adding a leading `.` pathspec makes the excludes inert entirely. Pass the exclusions alone.

Adapt the exclude list to the repo. Recon already reported the layout, so use it: a repo with `dist/`, `__snapshots__/`, or a `proto/gen` directory needs those added.

- **Reviewable**: additions plus deletions of human-authored code. What the budget applies to.
- **Raw**: everything. What the reviewer sees, and worth reporting even when it does not count against the budget, because a 3,000 line lockfile diff still costs review attention.

A rewritten line counts twice, once as an addition and once as a deletion, so 500 reviewable is roughly 250 rewritten lines or 500 brand new ones.

Log both numbers in the ledger at each chunk end.

**Past about 400 reviewable lines, close the slice at the next atomic boundary**: verify it, ship its PR, open the next slice. Do not let it swell past the budget. The exception is a logged cohesion exception from the plan.

Estimates miss. The running count is what catches what the plan got wrong.

## When a chunk goes wrong

**Two failed attempts at the same thing means stop.** A third variation of a wrong approach does not become right.

**Restart from the plan rather than patching fix on fix.** A chunk that drifted badly or failed twice gets reverted and re-delegated from an amended plan. Amend the plan first, log the amendment in the ledger, then delegate again with the corrected scope. Stacking fixes on a bad foundation produces code nobody can review and a diff nobody can explain.
