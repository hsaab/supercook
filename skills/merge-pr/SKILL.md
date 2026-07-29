---
name: merge-pr
description: Drives a pull request to merged. Resolves conflicts, triages review comments, fixes in-scope CI failures, re-runs stalled or flaky checks, then merges with the repo's default method. Handles stacked PRs bottom-up with the retarget and rebase lifecycle. Use when the user wants a PR actually merged rather than just kept healthy.
disable-model-invocation: true
---

# Merge PR

Take a PR from open to merged. Invoking this skill is the consent to merge.

Built-in `/babysit` is the no-merge version: it keeps a PR healthy but stops short of merging. This skill reuses that readiness work and adds the two things it deliberately does not do, which are the merge itself and walking a stack.

## Contents

- [The loop](#the-loop)
- [Comment triage](#comment-triage)
- [CI failures](#ci-failures)
- [Merging](#merging)
- [Stacked PRs](#stacked-prs)
- [What never happens](#what-never-happens)

## The loop

Pick the target: the PR named by the user, or the one for the current branch. On a stack, start at the bottom.

```bash
gh pr view <n> --json state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup
```

Then repeat until mergeable and green:

1. **Conflicts**: resolve them. Never discard someone else's side without understanding it.
2. **Comments**: triage per below.
3. **Failing checks**: fix in scope, report out of scope.
4. **Stalled or flaky checks**: re-run once with `gh run rerun <run-id> --failed`. The run id is required; without it the command needs a TTY and will fail. Get it from `gh pr checks <n>` or `gh run list --branch <branch>`.
5. **Re-read state.** A push invalidates the previous rollup.

Report progress as you go, one line per meaningful change, in plain language naming files.

## Comment triage

Read every comment. Then decide, per comment, rather than obeying by default.

- **A real bug or a correct concern**: fix it, and reply saying what changed and where.
- **A style preference the repo does not enforce**: acknowledge and move on. Do not restructure working code for a preference.
- **Wrong about the code**: say so, with the file and line as evidence. Politely, but do not change correct code to satisfy an incorrect review.
- **Out of scope**: agree it matters, note it as a follow-up, keep it out of this diff.

**Bot comments get read skeptically**, including Bugbot. They are useful and they are also confidently wrong sometimes, especially about intent and about code they cannot see the callers of. Verify the claim against the actual code before acting on it. A bot finding you disagreed with is worth a one-line reply explaining why.

## CI failures

Read the actual log before touching anything. `gh run view <id> --log-failed` beats guessing from the check name.

- **Caused by this PR**: fix it. That is in scope by definition.
- **Broken on the base branch too**: report it, do not absorb someone else's breakage into this PR.
- **Flaky**: re-run once. Twice is not flaky, it is failing, so investigate.
- **Infrastructure or credentials**: report it. Not something to work around.

## Merging

Merge only when the PR is genuinely ready: mergeable, required checks green, required approvals present.

```bash
gh pr merge <n> --squash    # or --merge / --rebase, matching the repo's default
```

Match the repo's configured default method rather than imposing one.

Delete the branch after merge when that is the repo's habit, but **on a stack, capture the branch tip SHA first**. The children's rebase needs it, and a deleted branch takes it with it.

## Stacked PRs

Merge bottom-up, one at a time. After each merge the children need attention, and what they need depends on how the base merged.

**The mechanics live in one place**, the supercook delivery guide at `skills/supercook/pipeline/delivery.md`, under "The stack lifecycle". Follow it rather than a second copy here. Three things matter enough to repeat:

**Capture `OLD_BASE=$(git rev-parse origin/<base-branch>)` before merging**, and before deleting the branch. The rebase needs it as its upstream, and deleting the branch first makes it unrecoverable.

**Do not ask `gh` for the merge method.** There is no such field. Use the ancestor test in the delivery guide, which asks whether the base's old commits still exist in the new base. That is the actual question, and it is answerable.

**`--force-with-lease` is irreversible, so ask every time**, even though invoking this skill consented to the merge. Consent to merge is not consent to rewrite a branch.

## What never happens

- **No force merge.** Branch protection, missing approvals, and failing required checks get reported, never bypassed. No admin override.
- **No skipped checks.** Not with `--admin`, not by disabling a required check.
- **No discarded work.** Not in a conflict resolution, not in a rebase.
- **No merging a PR the user did not point at.** One target, or one explicit stack.
- **No em dashes** in comments, replies, or commit messages.

If the PR cannot merge, say exactly why in one plain-language line and stop. A blocked merge reported honestly is a good outcome. A merged PR that skipped a gate is not.
