# Phase 9: merge

Take a PR from open to merged. One loop, whatever state the PR is in.

This phase only runs when the user asked for a merge. Nothing here fires because a PR happened to look mergeable. See [../playbooks/merge.md](../playbooks/merge.md) for the trigger and entry rules.

Built-in `/babysit` is the no-merge version: it keeps a PR healthy but stops short of merging. This phase does that readiness work and adds the two things babysit deliberately does not do, which are the merge itself and walking a stack.

## Contents

- [The loop](#the-loop)
- [Waiting is not blocked](#waiting-is-not-blocked)
- [Comment triage](#comment-triage)
- [CI failures](#ci-failures)
- [Merging](#merging)
- [Stacked PRs](#stacked-prs)
- [Ledger rows](#ledger-rows)
- [What never happens](#what-never-happens)

## The loop

Pick the target: the PR named by the user, or the one for the current branch, or the run's own PR when this phase follows phase 8. On a stack, start at the bottom.

```bash
gh pr view <n> --json state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup
```

Then repeat until mergeable and green:

1. **Conflicts**: resolve them. Never discard someone else's side without understanding it.
2. **Comments**: triage per below.
3. **Failing checks**: fix in scope, report out of scope.
4. **Stalled or flaky checks**: re-run once with `gh run rerun <run-id> --failed`. The run id is required; without it the command needs a TTY and will fail. Get it from `gh pr checks <n>` or `gh run list --branch <branch>`.
5. **Re-read state.** A push invalidates the previous rollup, and a PR that has been open a while accumulates base drift between passes.

Report progress as you go, one line per meaningful change, in plain language naming files.

## Waiting is not blocked

Checks still running is not a reason to end the turn. Poll, keep the row open, and say what is in flight:

```bash
gh pr checks <n>            # what state are they in right now?
```

`[!]` blocked is reserved for what a human has to change: a missing required approval, branch protection, absent credentials, a decision only the user can make. Those are sanctioned pauses, written down as a ledger row.

Ending a run because CI was mid-flight is a silent stall, which the continuation protocol in [../SKILL.md](../SKILL.md#continuation-protocol) bans.

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

A fix made here is still a diff, so it obeys the same rules as any other: surgical, explained by naming the file and the consequence, and committed with its own message.

## Merging

Merge only when the PR is genuinely ready: mergeable, required checks green, required approvals present.

```bash
gh pr merge <n> --squash    # or --merge / --rebase, matching the repo's default
```

Match the repo's configured default method rather than imposing one.

Delete the branch after merge when that is the repo's habit, but **on a stack, capture the branch tip SHA first**. The children's rebase needs it, and a deleted branch takes it with it.

## Stacked PRs

Merge bottom-up, one at a time. After each merge the children need attention, and what they need depends on how the base merged.

**The mechanics live in one place**, [delivery.md](delivery.md#the-stack-lifecycle) under "The stack lifecycle". Follow it rather than a second copy here. Two things are worth repeating, because this phase can run in a session where phase 8 never did:

**Capture `OLD_BASE=$(git rev-parse origin/<base-branch>)` before merging**, and before deleting the branch. The rebase needs it as its upstream, and deleting the branch first makes it unrecoverable.

**Do not ask `gh` for the merge method.** There is no such field. Use the ancestor test in the delivery guide, which asks whether the base's old commits still exist in the new base. That is the actual question, and it is answerable.

## Ledger rows

This phase writes rows like any other. One per loop concern, so a context reset resumes the PR instead of re-deriving its state:

```
- [ ] merge (PR #412)
  - [x] conflicts: resolved src/queue/worker.ts, kept both sides of the retry branch (14:02)
  - [x] comments: 3 read, 1 fixed, 2 answered as out of scope (14:11)
  - [ ] checks: e2e-suite running, polling
  - [ ] merge
  - [~] children: skip: not a stack
```

## What never happens

- **No merge without an explicit ask.** The ask is what starts this phase, and it is never inferred.
- **No force merge.** Branch protection, missing approvals, and failing required checks get reported, never bypassed. No admin override.
- **No skipped checks.** Not with `--admin`, not by disabling a required check.
- **No discarded work.** Not in a conflict resolution, not in a rebase.
- **No merging a PR the user did not point at.** One target, or one explicit stack.
- **`--force-with-lease` is irreversible, so ask every time.** Consent to merge is not consent to rewrite a branch.
- **No em dashes** in comments, replies, or commit messages.

If the PR cannot merge, say exactly why in one plain-language line and stop. A blocked merge reported honestly is a good outcome. A merged PR that skipped a gate is not.
