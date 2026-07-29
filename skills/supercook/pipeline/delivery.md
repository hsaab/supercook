# Phase 8: deliver

One PR per slice, opened as each slice closes. Not one batch at the end.

## Contents

- [PR body format](#pr-body-format)
- [Branching and stacking](#branching-and-stacking)
- [The stack lifecycle](#the-stack-lifecycle)
- [Splitting as a backstop](#splitting-as-a-backstop)
- [Handoff](#handoff)

## PR body format

Three sections, in plain language. This is the most-read output the whole workflow produces, so it gets the house style at full strength.

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

**When the repo has a PR template**, treat these three sections as the minimum content and fit them into the template's fields. Do not overwrite a template the team relies on.

No em dashes, here or anywhere.

## Branching and stacking

| Slice relationship | Branch from | PR base |
|---|---|---|
| Independent of other slices | default branch | default branch |
| Depends on the previous slice | the previous slice's branch | the previous slice's branch |

Record the stack order and each PR's base in the ledger. That record is what makes the restack possible later.

**Prefer shallow stacks.** Two or three deep is manageable. Past that, ship sequentially: open slice N+1 only after slice N merges. The restack cost below is why.

## The stack lifecycle

A stack is not finished when the PRs are open. When a base PR merges, its children need attention, and what they need depends on how the base merged.

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
  git push --force-with-lease            # ask first, every time
fi
```

**Do not try to read the merge method from `gh`.** `gh pr view --json` has no merge-method field, and `mergeCommit` returns an oid for every merge type, so it cannot answer this question. The ancestor test above answers it exactly instead: it asks whether the base's old commits still exist in the new base.

**Why the two branches differ.** After a true merge commit, the child's commits are already contained in the new base, so the ancestor test passes, a retarget alone is correct, and a rebase would only churn history. After a squash or a rebase merge, the base's commits exist in a different form under different SHAs, the ancestor test fails, and the child must be replayed or its PR will show the base's changes as its own.

**`push --force-with-lease` is irreversible, so ask every time**, per the irreversible tier in `SKILL.md`. Consent to merge a stack is not consent to rewrite each branch in it.

**Re-running checks.** A rebase and force-push re-triggers checks on its own, since the head SHA changed. A bare retarget does not, because nothing about the child's commits moved, so trigger them explicitly when the child's checks matter:

```bash
gh pr checks <child-pr>                  # what state are they in now?
gh run rerun <run-id> --failed           # a run id is required, this is not interactive
```

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
