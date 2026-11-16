# Merge

Take a PR from open to merged, only on an explicit ask. The built-in `/babysit` does the same readiness work without merging; this adds the merge itself and walking a stack.

## The loop

Start from `gh pr view <n> --json state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup`, at the bottom of a stack. Repeat until mergeable and green: resolve conflicts, triage comments, fix checks, then re-read the state, because a push invalidates the old rollup. Report one plain-language line per meaningful change.

**Waiting is not blocked.** Checks still running is not a reason to end the turn: poll `gh pr checks <n>`, keep the row open, and say what is in flight. `[!]` is for what a human must change: a missing approval, branch protection, absent credentials, a decision only the user can make.

## Comment triage

Read every comment and decide per comment rather than obeying by default.

- A real bug or a correct concern: fix it, and reply saying what changed and where.
- A style preference the repo does not enforce: acknowledge and move on.
- Wrong about the code: say so, citing the file and line. Do not change correct code to satisfy it.
- Out of scope: agree it matters and note it as a follow-up, outside this diff.

Read bot comments skeptically, Bugbot included: verify the claim against the code before acting, and reply in one line when you disagree. A code fix is a `supercook-implementer` launch you check like any other.

## CI failures

Read the log first (`gh run view <id> --log-failed`).

- Caused by this PR: fix it.
- Broken on the base branch too: report it rather than absorbing it.
- Flaky: re-run once with `gh run rerun <run-id> --failed` (the id comes from `gh pr checks <n>`). Failing twice is not flaky.
- Infrastructure or credentials: report it.

## Merging

Merge only when it is mergeable, required checks are green, required approvals are present, and any UI smoke recorded in the PR body is current for this head. Use the repo's default method (`gh pr merge <n> --squash`, `--merge`, or `--rebase`). On a stack, merge bottom-up per [stacking.md](stacking.md): first state the whole sequence and the rewrites it needs, as a progress note and a ledger row. On Graphite, `gt merge --dry-run --no-interactive` is that statement; then run `gt merge --no-interactive` followed by the sync and submit from stacking.md. A surprise mid-walk gets handled, the new sequence gets logged, and the walk continues.

## Never

- Merge without an explicit ask, or merge a PR the user did not point at.
- Bypass branch protection, approvals, or required checks (no `--admin`).
- Discard someone else's work in a conflict or a rebase.
- Force-push a branch that is neither the run's own nor part of the stated walk without asking.

If the PR cannot merge, say exactly why in one plain line and stop. A blocked merge reported honestly is a good outcome.
