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

A stack is not finished when the PRs are open. When a base PR merges, its children need attention, and what they need depends on how it merged.

```bash
# 1. Which merge method did the base use?
gh pr view <base-pr> --json mergeCommit,state

# 2. Retarget every child, always
gh pr edit <child-pr> --base <new-base>

# 3. Replay history, only if the base was squashed or rebased
git rebase --onto <new-base> <old-base> <child-branch>
git push --force-with-lease
```

Two things to get right:

**The retarget is unconditional.** Every child pointing at a merged branch needs a new base.

**The replay is conditional.** After a true merge commit, the child's commits are already contained in the new base, so a retarget alone is correct and a rebase just churns history. After a squash or a rebase merge, the child carries commits that now exist in a different form on the base, so it must be replayed or the PR shows the base's changes as its own.

`push --force-with-lease` is an irreversible action. Ask once, per the risk tiers in `SKILL.md`.

Then re-run checks on each retargeted PR, since its base changed underneath it.

## Splitting as a backstop

The built-in `/split-to-prs` flow is the fallback, not the plan. Use it in two cases:

- A diff that still landed oversized despite the budget.
- The open-pr track, where the work already existed in the tree before supercook saw it.

What makes a late split survivable is the per-unit commit discipline from phase 6: each commit is one atomic change with its own message, so the split carves along real boundaries instead of guessing.

## Handoff

Choose based on what the user asked for:

- **Nothing more**: report and stop. The PR is open.
- **Keep it healthy**: hand to built-in `/babysit`. It triages comments, fixes CI, and resolves conflicts without merging.
- **Get it merged**: `/merge-pr`. Invoking it is the consent to merge, and it walks a stack bottom-up using the lifecycle above.

**The final reply** is short outcome sentences, in the same plain-language style as the PR body. What changed, in which files, and what it means. Not a wall of text, and not a recap of the process.
