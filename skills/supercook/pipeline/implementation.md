# Phases 5 and 6: test-first, then implement

Tests define done, and they get committed before the code that satisfies them. Then implementation happens in surgical chunks with the parent checking every one. The only retrospective exception is contract-level UI on the open-pr track, where the source already exists.

## Contents

- [Phase 5: test-first](#phase-5-test-first)
- [Phase 6: implement](#phase-6-implement)
- [The guards](#the-guards)
- [UI contract guard](#ui-contract-guard)
- [Line accounting](#line-accounting)
- [When a chunk goes wrong](#when-a-chunk-goes-wrong)

## Phase 5: test-first

Launch `supercook-test-designer` with the slice, its journeys from `plan.md`, the
test command, and the repo's test conventions. Set `verification: tests` when the
runner works, otherwise `verification: recipe`. A contract-level UI slice also gets
its referenced entries from the `UI source of truth` block and that slice's owned
obligations.

**Design from journeys, not from code.** Name who uses this and what they are trying to do, write those as tests with names a non-engineer could read, then add the realistic variations: bad input at a real entry point, empty state, the retry, permission denied. An edge case earns a test only when it sits on a path a user can actually reach.

For designed UI, semantic grouping and contracted DOM order are user-visible
behavior, not implementation details. The suite must assert every owned region by
its stable locator, repeated-item counts, semantic containment, and required
interactions. Exactly one named owner per contract asserts global logical DOM order
with the exact name recorded in its `order test` field.

Do not claim that a DOM test proves columns, widths, wrapping, or responsive
placement. An existing browser test may cover those; otherwise rendered smoke does.
Do not add a browser framework or pixel snapshots only for this gate.

**Commit per slice, not all at once.** The suite is designed once for the whole task, but each slice's tests land at the start of that slice. That way every PR carries its own red-to-green story and merges green. Committing the entire failing suite up front would leave slice 1's PR holding red tests for slices 2 and 3, and it could never merge.

Single-slice work collapses to the simple case: whole suite committed first.

**Verify the failure before moving on.** Each new test must fail because the behavior is missing, not because of a typo or a bad import. A test failing for the wrong reason sends the implementer chasing a phantom.

**Open-pr retrospective exception.** Existing contract-level UI can be missing its
structural assertions even though source already landed. Launch the test designer
with `mode: retrospective-open-pr`, run the assertions against the current diff,
and record pass or a contract gap honestly. Do not claim red-first evidence, and do
not launch the implementer from this track.

**Late current-run UI escalation.** If diff inspection upgrades a trivial chunk to
contract after this run wrote source, preserve its patch as evidence and restart
that chunk on a clean branch or worktree from the recorded pre-chunk base. Do not
stack a revert on top of the implementation commit and call that test-first.
Preserve unrelated user work, run the contract verification red, then re-delegate
implementation. Retrospective mode is not a shortcut for source this run authored.

**Where every commit must be green.** Some repos require it. Keep the red evidence in the ledger, then squash the test commit together with the implementation commit before pushing. The discipline survives; only the history shape changes.

**Where there is no test runner.** The test designer returns an executable recipe:
a script or command sequence with setup, assertions, expected output, and cleanup.
The parent writes it to `verification-<slice>.md` in the run folder and records that
path under the slice in `plan.md`, or in the retrospective ledger contract on
open-pr. In red-first mode the recipe must demonstrate the missing behavior; in
retrospective mode it reports pass or gap. The verifier runs that exact recipe.
Ordered prose that cannot execute is not a recipe.

Before accepting the test designer's return, run the
[UI contract guard](#ui-contract-guard) for every contract-level slice.

## Phase 6: implement

One `supercook-implementer` launch per slice, or per chunk within a slice when a slice has natural internal steps.

Before a trivial or other direct chunk that had no plan, record a restart point in
the ledger:

```text
pre-chunk: base <HEAD sha> | late-escalation patch <run-folder>/chunk-1.patch
```

Reserve that patch path before launch. If late UI detection fires, write the
run-authored diff there before abandoning the chunk and restart from the recorded
base in a clean branch or worktree. Without git, copy the scoped files and an
absent-file manifest into the run folder before launch instead.

Each launch gets:

- **An explicit file list**, the only files it may touch.
- **The data shape**, so it does not invent one.
- **The failing tests or recorded recipe to green**, by name.
- **The exact verification command.**
- **UI evidence when the slice references a contract**: the entry, source locator,
  resolved brief, retained screenshot or artifact, and owned obligations.

Then, for every return, the parent does four things in this order:

1. **Run the guards** (below). Before committing, always.
2. **Read the diff yourself.** The agent's summary is a claim. Its diff is the evidence.
3. **Commit that unit**, with a message in the house style: what changed, in which file, why, and what it means.

   ```
   Read webhook retry count from the queue record

   handleWebhook referenced a retryCount variable that the queue rewrite
   deleted, so every inbound webhook threw on its first line. The attempt
   count now comes off the queue record, which is where that state lives.
   ```

   Not "fix webhook bug" or "improve retry handling". The subject says what changed, the body says why it was wrong and what it means.
4. **Update the ledger and the plan checkboxes**, with the running line counts.

Between launches, **re-anchor**: name the open ledger row the next action serves. Cannot name one? That is drift. Log a course-correction row and get back on an open row.

## The guards

A boundary written in a prompt is a request. These are what make it a control.

### Recipe integrity

An executable recipe lives in the ignored run folder, so Git status cannot protect
it. Before implementation, hash it and record the digest in the ledger:

```bash
RECIPE_SHA=$(shasum -a 256 "<run-folder>/verification-<slice>.md" | awk '{print $1}')
```

After every implementer return and again before verification, recompute and compare
the digest. The implementer may read the recipe but may never edit, replace, or
delete it. A mismatch invalidates the implementation result: restore the
run-authored source chunk through the scope guard or pre-chunk checkpoint,
regenerate the recipe through `supercook-test-designer`, record the new digest, and
re-delegate.

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

### UI evidence

For a contract-level UI slice, reject an implementer return that lacks
`design-evidence: direct <node>` or `design-evidence: provided <artifact>`. Confirm
the named evidence was part of the launch and that the diff satisfies only the
slice's owned UI obligations.

If the diff changes hierarchy, region order, geometry, interactions, or responsive
behavior on a slice classified as `no layout change`, reopen the UI contract gate.
The implementer cannot grant itself that skip.

A divergence from logical DOM order or any other material design change returns to
the parent for deviation approval. It is not fixed by weakening the structure test.

## UI contract guard

For each contract entry, take only the literal `anchor` values named in this
slice's `ui-obligations` and run fixed-string searches against the changed test
paths, or against the recorded `verification-<slice>.md` recipe. Run the order-name
search only when `ui-order-test: owner`:

```bash
rg -F -- '<region anchor>' <test paths or verification-recipe path>
# order-test owner only
rg -F -- 'UI-1 renders regions in design order' <test paths or verification-recipe path>
```

Every applicable command must find a match. On the order-test owner, confirm the
named order test:

1. compares actual element positions rather than only checking presence
2. is not skipped, marked todo, or conditionally disabled
3. fails because the unimplemented order is wrong
4. passes only after the implementation matches the contract

Run the focused command and record the real failure. Grep is the binary
traceability guard; the executed comparison is the semantic proof. Missing anchors,
counts, grouping, interactions, or order return to `supercook-test-designer` before
implementation starts.

In `retrospective-open-pr` mode, replace steps 3 and 4 with an honest pass or gap
against the existing diff. The guard still requires the real position comparison
and focused test output.

With no test runner, require one executable structural recipe that checks the same
obligations, write it in the run folder, link it from the plan or open-pr ledger,
and record `verification: recipe`. A missing runner is not permission to omit the
contract.

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
