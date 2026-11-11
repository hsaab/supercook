# Phase 8: deliver

One PR per slice, opened as each slice closes. Not one batch at the end.

## Contents

- [PR body format](#pr-body-format)
- [Evidence section](#evidence-section)
- [UI delivery guard](#ui-delivery-guard)
- [Branching and stacking](#branching-and-stacking)
- [The stack lifecycle](#the-stack-lifecycle)
- [Slice size fail-closed](#slice-size-fail-closed)
- [Pre-PR check](#pre-pr-check)
- [Splitting as a backstop](#splitting-as-a-backstop)
- [Handoff](#handoff)

## PR body format

Three sections, in plain language, plus the `## Evidence` section below. Evidence always applies. This is the most-read output the whole workflow produces, so it gets the house style at full strength.

```markdown
## Why we did this
What was wrong or missing, in terms of the actual code and its real consequence.
Name files and functions. Someone who has never seen this repo should follow it.

## What the outcome is
What now works that did not before. Name the files that changed and what each one
does now. Connect each change to the behavior it produces.

## Operational tasks
- [ ] anything a human has to do: env var, migration, feature flag, dashboard, rollback note
```

Write it the way a sharp junior engineer would explain their own work:

> `handleWebhook` in `src/api/webhook.ts` still referenced a `retryCount` variable that the queue rewrite deleted, so any real webhook hitting that endpoint threw before it did anything. It now reads the attempt count off the queue record, which is where that state actually lives since the rewrite.

Not this:

> Fixed webhook handling and improved retry logic for better reliability.

**When the repo has a PR template**, treat these three sections as the minimum content and fit them into the template's fields. Carry `## Evidence` into the template as its own section or field. Do not overwrite a template the team relies on.

No em dashes, here or anywhere.

When a UI contract applies, fit these facts into `What the outcome is` and
`Operational tasks`:

```text
UI source: <canonical design URL or artifact citation>
UI contracts: <UI-1, UI-2>
Approved deviations: <each one, or none>
Contract summary: <semantic order, rendered layout, responsive behavior, interactions>
Rendered smoke:
  head: <tested git SHA>
  start/readiness: <commands or signals>
  route/state: <path, seed or fixture, auth>
  viewports: <sizes>
  interactions/checks: <everything exercised and compared>
  result/time: <pass or sanctioned-blocked, timestamp>
```

This evidence is durable on the PR. A cold merge run cannot depend on the untracked
ledger still existing.

When an executable recipe replaces a test runner, include the exact recipe or a
durable repository link plus its expected checksum in `Operational tasks`. The
run-folder copy is not available to a cold merge session.

## Evidence section

A fourth section, `## Evidence`, makes the proof durable on the PR. The ledger and run folder are untracked, so a cold reviewer or merge session cannot read them.

```markdown
## Evidence
Red first (test commit <sha>, tests only):
- <test name>: <assertion line that failed before the code existed>

Those assertion lines were recorded against a temporary stub. Checking out that SHA
fails at import by design. On squash-only repos the SHA may disappear, so the test
names and assertion lines here are the durable proof.

| Acceptance criterion (verbatim) | Test or check | Passing output |
|---|---|---|
| AC-1: <text from acceptance.md> | <test name or command> | <quoted passing line> |

Built in solo mode, no independent review: verify was a self-audit.
```

- **Red first** lines come from the test-first row's `red-evidence`. Open-pr retrospective and trivial runs have no red test, so they omit the block and say so.
- **The table** appears only when `acceptance.md` exists. Every row quotes the verifier's proof. A row without proof means the PR does not open.
- **The solo line** appears only on solo runs, and links a hosted Bugbot run when one exists.
- **Proof lives here or in a PR comment, never in the diff.** QA notes, logs, width-sweep output, regen scripts, and test stubs stay out of the branch.

## UI delivery guard

Before creating or pushing a PR for a UI slice, read its rendered-smoke row from the
ledger.

- `pass`: delivery may continue.
- sanctioned-blocked because no renderer could load the target: delivery may
  continue only when the PR names the missing evidence and the manual checks.
- open or `fail`: do not create the PR. A failure returns to implementation through
  the gap loop in [verification.md](verification.md#the-gap-loop).

Run the same guard against the final composed-page smoke before declaring the run
done. After it runs, update the affected open PR bodies with the composed result and
tested head. A ledger row by itself is not enforcement; refusing delivery is.

## Branching and stacking

**Terminology.** A supercook **slice** is one unit of work: one branch and one PR. A supercook **stack** is a chain of dependent PRs. That maps 1:1 onto Graphite: a slice is a Graphite branch/PR in a stack, and a stack is a Graphite stack. The words stay distinct on purpose; do not rename slices to stacks.

| Slice relationship | Branch from | PR base |
|---|---|---|
| Independent of other slices | default branch | default branch |
| Depends on the previous slice | the previous slice's branch | the previous slice's branch |

Record the stack order and each PR's base in the ledger. That record is what makes the restack possible later, and it is what phase 9 reads when walking a stack.

**Hard cap: 3 PRs open in one chain at any time.** Slice 4 of a chain opens only after the chain drops below 3 open PRs, which happens when its bottom PR merges. Branching is unaffected: implementation keeps chaining branches locally, only the PR opening waits. The cap exists for reviewer load: three open diffs in one chain is already a lot to keep in a human head, even when restacking is cheap.

### When intake recorded `stacking gt`

Use Graphite for branch creation and PR open. Independent slices still start from the default branch; dependent slices stack on the previous slice's branch.

If this run already has a plain `git`/`worktree` branch (intake often creates `supercook/<slug>` that way), bring it into Graphite before stacking further children:

```bash
gt track --force --no-interactive          # parent = nearest tracked ancestor (usually trunk)
```

Then, for each dependent slice (or the first commit on a tracked run branch):

```bash
gt create --all --message "<slice commit message>" --no-interactive
gt submit --stack --no-interactive --no-edit --publish
# then set the house-style body (gt submit has no body flag):
gh pr edit --body-file <path-to-three-section-body>
```

Always pass `--no-interactive` (and `--no-edit` on submit for new/updated PRs) so agent runs do not hang on prompts. Write the three-section PR body from earlier in this file via `gh pr edit` (or the repo's template flow) right after submit; do not leave Graphite's default description in place.

`gt submit` force-pushes with lease by design. On branches this run owns, that is a reversible-tier write per [../SKILL.md](../SKILL.md#autonomy-host-permissions-first): run it, log it. Outside a merge-ask walk, ask only when the branch is not ours or the host requires approval.

Each Graphite PR is an ordinary GitHub PR. Reviewers, CI, branch protection, and CODEOWNERS all stay on GitHub. The Graphite web app is optional.

### When intake recorded `stacking manual`

Create branches and open PRs with `git` and `gh` as before, setting each dependent PR's base to the previous slice's branch. The restack mechanics below under "Manual path" apply after each base merges.

## The stack lifecycle

A stack is not finished when the PRs are open. When a base PR merges, its children need attention.

### Graphite path (`stacking gt`)

After a base PR merges (or after someone merges mid-stack from the GitHub UI), restack and update remotes from **this run's working tree**:

```bash
gt sync --no-interactive --delete-all    # fetch trunk, retarget, restack, clean up merged branches
gt submit --stack --no-interactive --no-edit --update-only
```

That replaces the `OLD_BASE` capture, `gh pr edit --base`, ancestor test, and `git rebase --onto` sequence. Run it from the run's working tree; gt skips branches checked out elsewhere. `--no-interactive` (and `--delete-all` on sync when cleanup is intended) keeps agent runs from hanging on delete/restack prompts. Consent for the force-with-lease that `gt submit` performs follows [../SKILL.md](../SKILL.md#autonomy-host-permissions-first): run-owned stack branches are reversible-tier; a merge-ask walk already covers those rewrites. See [merge.md](merge.md#stacked-prs).

**Re-running checks.** A restack that changes the head SHA re-triggers checks on its own. That is the intended gate: each child is re-validated against the post-merge trunk before it can merge.

### Manual path (`stacking manual`)

**Record the base branch tip SHA before merging it.** The rebase below needs it as the upstream, and it becomes unrecoverable once the branch is deleted.

```bash
OLD_BASE=$(git rev-parse origin/<base-branch>)   # BEFORE the merge
```

After the base merges:

```bash
git fetch origin

# 1. Retarget every child. Always.
gh pr edit <child-pr> --base <new-base>

# 2. Decide whether history has to be replayed.
if git merge-base --is-ancestor "$OLD_BASE" origin/<new-base>; then
  echo "contained: retarget alone is correct, no replay"
else
  git rebase --onto origin/<new-base> "$OLD_BASE" <child-branch>
  git push --force-with-lease            # consent rules below
fi
```

**Do not try to read the merge method from `gh`.** `gh pr view --json` has no merge-method field, and `mergeCommit` returns an oid for every merge type, so it cannot answer this question. The ancestor test above answers it exactly instead: it asks whether the base's old commits still exist in the new base.

**Why the two branches differ.** After a true merge commit, the child's commits are already contained in the new base, so the ancestor test passes, a retarget alone is correct, and a rebase would only churn history. After a squash or a rebase merge, the base's commits exist in a different form under different SHAs, the ancestor test fails, and the child must be replayed or its PR will show the base's changes as its own.

**`push --force-with-lease` is irreversible**, per the irreversible tier in `SKILL.md`. Ask before each one, unless a merge-ask walk is in progress and this rewrite is part of the stated sequence: see [merge.md](merge.md#stacked-prs). Outside a stated walk, a merge ask is not consent to rewrite an unrelated branch.

**Re-running checks.** A rebase and force-push re-triggers checks on its own, since the head SHA changed. A bare retarget does not, because nothing about the child's commits moved, so trigger them explicitly when the child's checks matter:

```bash
gh pr checks <child-pr>                  # what state are they in now?
gh run rerun <run-id> --failed           # a run id is required, this is not interactive
```

## Slice size fail-closed

Before `gt submit`, `gh pr create`, or any PR open for a slice, measure **reviewable** lines from the merge base with the commands in [implementation.md](implementation.md#line-accounting). Lockfiles, generated output, vendored trees, and snapshots stay excluded.

**Over 500 reviewable lines, do not open the PR** unless that slice already has a cohesion `exception:` logged from the plan. The reason must be the one planning already requires: splitting would leave the default branch broken or unsafe between PRs.

With that exception already logged, open the PR.

Without that exception, split into more slices and open those as separate PRs. Do not mint the exception at PR-open time. An unexplained oversize PR is a defect.

Naming the work "one TDD slice", "slice E0", or "one eval harness" is not cohesion by itself. The exception still needs the same unsafe-between-PRs test as planning ([planning.md](planning.md#the-cohesion-exception)).

Every slice PR open in this section, whether under budget, opened with a logged cohesion exception, or opened from a backstop split, logs reviewable and raw counts on the deliver ledger row. Planning already requires both numbers on every slice ([planning.md](planning.md)).

This gate applies to a planned slice that is already openable: under budget, or over budget with a logged cohesion exception. Use [Splitting as a backstop](#splitting-as-a-backstop) and [open-pr.md](../playbooks/open-pr.md) only when there is no planned slice with a logged cohesion exception, for example an oversized diff without a plan exception or the open-pr track. Those paths do not invent a plan exception.

The parent-side guard runs here even when the plan named only one slice.

## Pre-PR check

Before `gh pr create`, `gt submit`, or any PR open, in every mode and on every tier, run this check from the run's working tree. It fails closed: any failure means the PR is not opened and the row that owns the gap reopens.

1. **Every row is settled.** Each ledger row above deliver is `[x]`, `[~]` with a valid reason, or a sanctioned `[!]`.
2. **The diff holds only scoped files.** Every path in `git diff --name-only <BASE>...HEAD` is in a plan slice's scope list or the test-first commit of its slice. On trivial tier, it is in the implementer's scope list, or the test-first commit when a test-designer ran because the change needed a test. A QA note, log, sweep output, regen script, or leftover stub fails the check. Move it to the run folder and cite it in the PR body.
3. **Every criterion has proof.** When `acceptance.md` exists, each criterion has a passing line in the verifier's output.
4. **The Evidence section is filled** per [Evidence section](#evidence-section), including the solo line on a solo run.

Log the result on the deliver row, naming the checks that ran.

## Splitting as a backstop

The built-in `/split-to-prs` flow is the fallback, not the plan. Use it in two cases:

- A diff that still landed oversized despite the budget.
- The open-pr track, where the work already existed in the tree before supercook saw it.

What makes a late split survivable is the per-unit commit discipline from phase 6: each commit is one atomic change with its own message, so the split carves along real boundaries instead of guessing.

## Handoff

Choose based on what the user asked for:

- **Nothing more**: report and stop. The PR is open. This is the default, and it is what happens unless a merge was actually asked for.
- **Keep it healthy**: hand to built-in `/babysit`. It triages comments, fixes CI, and resolves conflicts without merging.
- **Get it merged**: continue into phase 9, [merge.md](merge.md), which walks a stack bottom-up using the lifecycle above. Only on an explicit ask. A PR that looks mergeable is not an ask.

**The final reply** is short outcome sentences, in the same plain-language style as the PR body. What changed, in which files, and what it means. Not a wall of text, and not a recap of the process.
