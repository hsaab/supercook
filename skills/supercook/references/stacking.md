# Stacking

A slice is one branch and one PR. A stack is a chain of dependent slice PRs.

| Slice | Branch from | PR base |
|---|---|---|
| Independent | default branch | default branch |
| Depends on the previous slice | the previous slice's branch | the previous slice's branch |

Record the stack order and each PR's base in the ledger; the restack and the merge walk read it. **At most 3 PRs open in one chain**: slice 4 opens once the bottom PR merges. Branches keep chaining locally; only opening the PR waits.

## Which path

Use Graphite only when `gt` is installed, the repo is `gt init`-ed (`test -f "$(git rev-parse --git-path .graphite_repo_config)"`), and `gt auth` does not print `No auth token set`. Otherwise use the manual path, and switch to it if a `gt` command later fails on auth. On a cold merge, a stack that was never `gt track`-ed stays manual. Log the path you picked. Run every `gt` command from the run's working tree, and free any stack branch checked out in another worktree, because `gt` skips those and leaves them stale.

## Graphite path

```bash
gt track --force --no-interactive                       # once, if the run branch was made with plain git
gt create --all --message "<slice commit message>" --no-interactive
gt submit --stack --no-interactive --no-edit --publish
gh pr edit --body-file <body>                           # gt submit has no body flag
```

After a base merges, a review fix lands on a base slice, or someone merges mid-stack in the GitHub UI:

```bash
gt sync --no-interactive --delete-all
gt submit --stack --no-interactive --no-edit --update-only
```

`gt submit` force-pushes with lease. On branches the run owns that is a reversible write; log it.

## Manual path

Open PRs with `git` and `gh`, each dependent PR based on the previous slice's branch. Before a base merges, capture its tip, because deleting the branch loses it:

```bash
OLD_BASE=$(git rev-parse origin/<base-branch>)
```

After it merges:

```bash
git fetch origin
gh pr edit <child-pr> --base <new-base>
if git merge-base --is-ancestor "$OLD_BASE" origin/<new-base>; then
  echo "contained: the retarget alone is correct"
else
  git rebase --onto origin/<new-base> "$OLD_BASE" <child-branch>
  git push --force-with-lease
fi
```

`gh` has no merge-method field, so do not ask it. The ancestor test answers the real question: after a merge commit the child's history is contained; after a squash or rebase merge it is not, and the child must be replayed or its PR shows the base's changes as its own. A bare retarget does not re-run checks; use `gh run rerun <run-id> --failed` when they matter.

After a review fix is pushed to a base slice that has not merged, replay each child on it, bottom-up: `git rebase origin/<base-branch> <child-branch>`, then `git push --force-with-lease`. Ask before force-pushing a branch the run does not own.
