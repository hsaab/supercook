# Playbook: review

Slice PRs exist. Run the external reviewers on each one, implement the real findings, and merge only when the ask included it.

## Trigger and entry

**Trigger: an explicit review ask, whenever it arrives.** `/supercook review`, `/supercook review PR 412`, or `/supercook review and merge`, in the invocation or mid-run after phase 8 opened the slice PRs. Nothing else selects this track. The assessor never routes here on its own, and **phase 1 does not run**: the parent routes review before assessor per [../SKILL.md](../SKILL.md#user-selected-track-routing).

**The ask decides the mode, and the mode is fixed at intake.**

- `review`: review, fix, verify, and stop at healthy open PRs with a findings summary per PR.
- `review and merge`: the same work, then continue into phase 9 per [merge.md](merge.md) and [../pipeline/merge.md](../pipeline/merge.md).

A clean review never upgrades itself into a merge. Record `mode: review` or `mode: review+merge` in the ledger header so a resumed session cannot guess wrong. On the same header, write `models:` as one ` | `-separated line listing **every** roster key with its resolved form, the same rule as [../pipeline/intake.md](../pipeline/intake.md) and [../pipeline/ledger.md](../pipeline/ledger.md): `<role> <slug>` when the slug will be passed, or `<role> inherit (unavailable <slug>)` when intake announced a fallback. Resolve once at intake per [../models.md](../models.md) so a resume launches with the same models instead of re-resolving.

**Entry: continue a run if one exists, otherwise open one.**

- **The ask lands inside a live run.** Reuse the existing ledger and the stack context phase 8 just built. No new run, no second ledger.
- **The ask arrives cold.** Intake seeds a run on this track around the target PRs. Targets are the named PRs, or the current branch's PR plus every open PR stacked on it. Record the stack order and each PR's base branch in the ledger before reviewing anything.

Stacking mechanics follow the `stacking gt | manual` capability intake records. On cold entry apply the same tracked-branch check as the merge track: `stacking gt` only counts for a stack whose branches appear in `gt log`, with `gt track --force --no-interactive` allowed when the parent bases are clear, otherwise this stack walks the manual path.

## Steps

Copy these into the ledger verbatim. On a **stack**, treat the block below as **one nested checklist per PR** (bottom-up), not one flattened list for the whole stack.

```
- [ ] resolve targets: named PRs or the current branch's PR and its stack; record bottom-up order and each PR's base (see Multi-PR stacks)
- [ ] stack walk (bottom-up): for each PR in order, nest one ledger block and run every row below inside it before opening the next PR's block
  - [ ] PR #___ (base ___): check out the branch; resolve each of bugbot and security-review to `hosted`, `local`, or `pending` against the PR head per "Reuse hosted Bugbot and security review"
  - [ ] PR #___: launch both thermo reviewers plus every `local` reviewer in one parallel batch, scoped to this PR's base; collect `hosted` findings from the PR
  - [ ] PR #___: once every reviewer has reported (each `pending` one resolved, then collected or launched locally), dedupe and triage findings; decline the rest with a stated reason
  - [ ] PR #___: one supercook-implementer launch (review-implementer model) fixes all in-scope findings as one-commit diffs
  - [ ] PR #___: run the recorded tests (and rendered smoke on a UI contract), then push
  - [ ] PR #___: one confirmation pass on the reviewers whose findings were implemented, sources resolved again against the pushed head; the row stays open until each of them has reported
  - [ ] PR #___, only when the confirmation pass found in-scope findings: one more implementer launch, run the recorded tests, push; no confirmation pass after it
  - [ ] PR #___: wait for CI checks only; review-bot checks are covered by the source decision and the confirmation pass
  - [ ] PR #___, merge mode only: merge **this PR only** via phase 9 after every review row above for this PR is checked (never bulk-merge the stack before lower PRs complete review)
  - [ ] PR #___, after merge or review-only fixes on a base slice: restack children (gt or manual per the ledger's stacking capability), then continue to the next PR up
- [ ] review mode only (all PR blocks done): report the per-PR findings summary and stop at open PRs
```

## Multi-PR stacks, ledger, and merge mode

**Resolve the full stack at intake** before any reviewer launches. Named PR numbers in the ask, or the current branch's PR plus every open PR stacked on it (`gh pr list` and each PR's base branch to build the chain). Record **bottom-up order** and each PR's base in the ledger header and in one **nested block per PR** (see [The ledger is not optional here](#the-ledger-is-not-optional-here)).

**Bottom-up, one PR at a time.** Finish the full fan-out, triage, implementer, verify, confirmation pass, and CI wait for PR *N* before starting PR *N+1*. Fixes on a base slice change what children sit on; reviewing or merging children first wastes work and skips the playbook on the wrong diff.

**Merge mode (`review and merge`) merges one PR per cycle, not the whole stack at once.**

1. Complete every review row for the bottom open PR.
2. Run phase 9 for **that PR only** ([merge.md](merge.md) loop: comments, CI, conflicts, merge).
3. Restack children ([Order on a stack](#order-on-a-stack)).
4. Open the next PR's nested ledger block and repeat from step 1.

Never call `gt merge` / bulk `gh pr merge` on the full stack, and never jump to the tip because "the stack was already reviewed at the tip." Each PR gets its own reviewer batch scoped to **its** base branch.

## Reuse hosted Bugbot and security review

Bugbot and security review often already ran on the PR as hosted review bots. When one did, its findings are the review: read them from the PR instead of paying for the same review twice. The thermo reviewers have no hosted form and always run locally.

Resolve each of the two reviewers to `hosted`, `local`, or `pending` against the PR's current head commit. List the head's check runs:

```bash
HEAD_SHA=$(gh pr view <n> --json headRefOid --jq .headRefOid)
gh api --paginate "repos/{owner}/{repo}/commits/$HEAD_SHA/check-runs" \
  --jq '.check_runs[] | {name, app: .app.slug, status, conclusion, started_at, output}'
```

Only check runs from the `cursor` app count, so a third-party check with a similar name never stands in for a review. Bugbot's check is named exactly `Cursor Bugbot`; `Cursor Bugbot Autofix` is a different check and never counts. Security review has no confirmed hosted check name yet, so it always resolves to `local`. Once its exact check name is known, add it here the same way, never as a partial match: the `cursor` app also posts user-named checks such as `Cursor Approval Agent: <name>`. When one name has several runs on the head, the latest `started_at` wins. Take the first row that matches:

| That reviewer's check run on the head | Source |
|---|---|
| completed, conclusion `success` or `neutral`, and `output.summary` says `completed review` | `hosted` |
| completed any other way, including `neutral` without `completed review` (the `cursor` app also reports `neutral` for a run that failed to start) | `local`, because a crashed or skipped bot is not a review |
| not completed yet (queued, waiting, requested, or in progress), started less than 30 minutes ago | `pending` |
| none yet, and the head was pushed less than 10 minutes ago | `pending`, since hosted bots take a moment to start |
| none, or still not completed after 30 minutes | `local`; a run that only exists on an older commit missed the code pushed since |

The push time is known when this run pushed the head itself. On a cold start, use the head commit's committer date; when that is older than the real push, the only cost is a local review that a hosted one would have covered.

**A pending run never holds the fan-out.** Launch the local batch right away and keep resolving the pending reviewer against the table until it lands on `hosted` or `local`. If it lands on `local`, launch that reviewer then, and ignore any hosted result that arrives later for this head, so each reviewer has one source of truth. Triage waits until every pending reviewer has resolved and reported.

Hosted findings come from three places, each filtered to the Cursor bot as author (login `cursor`) and to the head commit, so neither someone else's comment nor a finding left on an older commit passes as a new one:

- the check run's `output` (title, summary, text) from the command above
- review bodies left on the head commit:

```bash
gh pr view <n> --json reviews \
  --jq "[.reviews[] | select(.author.login == \"cursor\" and .commit.oid == \"$HEAD_SHA\") | .body]"
```

- review threads whose first comment's `originalCommit` is the head commit and that are neither resolved nor outdated. REST does not expose either flag, so use GraphQL:

```bash
gh api graphql --paginate -F owner='{owner}' -F repo='{repo}' -F n=<n> -f query='
  query($owner: String!, $repo: String!, $n: Int!, $endCursor: String) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $n) {
        reviewThreads(first: 100, after: $endCursor) {
          pageInfo { hasNextPage endCursor }
          nodes { isResolved isOutdated path line
            comments(first: 1) { nodes { author { login } originalCommit { oid } body } } }
        }
      }
    }
  }'
```

Record each reviewer's source (`pending` until it resolves), the head SHA it was judged against, and the check run's conclusion in the ledger. Hosted findings go through the same dedupe and triage as local ones; being on the PR earns them no extra trust.

## The reviewer fan-out

Up to four reviewers per PR, launched in parallel in one message, each with a fresh context: both thermo reviewers always, plus `bugbot` and `security-review` when their source is `local`. These are host subagents with their own fixed contracts, not supercook agents, but they still take a model from the roster: pass the resolved `reviewer` slug from [../models.md](../models.md) on every launch, including the confirmation pass. `inherit` means omit the model field, same as every other role. A `hosted` reviewer runs on its own service, so no model applies. Tag every local reviewer launch with `supercook-role: reviewer` and `supercook-run: <run folder>` (same run folder as the parent supercook run). Tag the finding-fix launch with `supercook-role: review-implementer` and the same run tag.

**Parallel means one batch.** All local reviewer launches go out as a single batch of Task calls; the one exception is a pending hosted reviewer that falls back to `local` after the batch went out. Never launch one reviewer, wait for it, then launch the next; none of them depends on another's output, so a sequential fan-out multiplies the wall time for nothing. The confirmation pass follows the same rule: every reviewer being rerun locally launches in one batch. Parallelism stays within one PR because the diff-computing reviewers read the checked-out working tree and only one PR branch can be checked out at a time, so it is one PR at a time, all local reviewers at once within it.

First check out the PR's branch (`gh pr checkout <n>`), because the diff-computing reviewers read the working tree.

**`bugbot`** and **`security-review`** compute the diff themselves from the repository path. Launch each with exactly this prompt shape:

```
Full Repository Path: <absolute path to this run's working tree>
Diff: branch changes
Base Branch: <this PR's base branch>
Custom Instructions:
supercook-role: reviewer
supercook-run: <run folder>
```

The roster hook parses the first line-anchored `supercook-role:` and `supercook-run:` in the prompt, including inside `Custom Instructions:`, so the tags must stay in that block without altering the required fields above.

**`Base Branch` is what scopes a stacked slice.** A child PR's base is the previous slice's branch, not the default branch. Omitting it makes every reviewer see the whole stack's diff and report the parent slices' code as this PR's, so the findings land on the wrong PR.

**`thermo-nuclear-review-subagent`** and **`thermo-nuclear-code-quality-review-subagent`** do not compute the diff. Gather it first (`git diff <base-branch>...HEAD` plus the full contents of the changed files that need context) and pass it in the prompt, asking each for prioritized findings with file references and evidence. Put the same `supercook-role: reviewer` and `supercook-run: <run folder>` tags at the top of that prompt (before the diff material).

**When a reviewer subagent is not installed on this host**, run the ones that exist, and record the gap as a ledger row and one line in the findings summary. Never fabricate a review, and never substitute a generic agent pretending to be one.

## Triage before implementing

Dedupe findings across every reviewer that reported, hosted and local, first: overlapping findings merge into one entry and carry more weight. Then triage each finding with the same skeptical-bot rule as [../pipeline/merge.md](../pipeline/merge.md#comment-triage). Reviewers are useful and also confidently wrong sometimes, so verify every claim against the actual code before acting on it.

- **A real bug or a correct concern**: fix it on this PR's branch.
- **A style preference the repo does not enforce**: decline, with the reason recorded.
- **Wrong about the code**: decline, naming the file and line that disproves it.
- **Out of scope for this slice**: note it as a follow-up, keep it out of this diff.

**Fixes always run in a subagent: one `supercook-implementer` launch per PR, on the `review-implementer` model.** The parent never edits source inline, not even for a one-line finding; the subagent is what keeps the fix on the right model with a clean context. That launch carries `supercook-role: review-implementer` and `supercook-run: <run folder>` like any other supercook subagent. Launch after every local reviewer has returned, every hosted reviewer's findings are collected, and triage is done, per the contract in [../agents.md](../agents.md), carrying:

- the full deduped in-scope findings list, one entry per finding with the file, the claim, and the evidence that survived triage
- the scope list: the union of files those findings name
- the PR's recorded test command as the verification

Boundaries are unchanged: never a test file, never a path outside the scope list. The parent keeps triage, declines, the confirmation-pass decision, and reads the returned diff itself before committing. If the confirmation pass produces new in-scope findings, that is a second implementer launch for this PR (still capped by the no-third-pass rule), not an inline patch.

Every fix is still a diff under the normal rules: change only what the finding needs, no opportunistic cleanup, one commit per atomic change, and an explanation naming the file and the real consequence. Record each decline in the ledger and in the PR (a comment or the findings summary), so the judgment survives a context reset.

## One confirmation pass, not a loop

After the fixes are pushed, re-run only the reviewers whose findings were implemented, once. Resolve each one's source again against the pushed head with the same table: a hosted bot that reruns on the push is read from that run, and one that never starts within 10 minutes runs locally instead, so a confirmation pass never silently goes missing. Local reruns use the same scoped prompt and launch in one batch. The confirmation row stays open until every reviewer in it has reported. New findings from that pass get triaged the same way, but there is no third pass: anything still open after the confirmation pass is reported on the PR rather than looped on. A push made for confirmation-pass fixes gets no confirmation pass of its own. Reviewers can disagree with each other's fixes forever, and this cap is what keeps a review from becoming a bot argument.

## Order on a stack

Bottom-up, one PR at a time. Fixes pushed to a base slice change what every child sits on, so a child reviewed before its parent settles gets reviewed against code that is about to move. See [Multi-PR stacks, ledger, and merge mode](#multi-pr-stacks-ledger-and-merge-mode) for ledger nesting and merge-mode pacing.

1. Review, fix, verify, confirmation pass, and CI wait for the bottom open PR (full playbook for that PR).
2. In merge mode, merge **only that PR** per phase 9, then restack the children as part of the walk before the next PR's review block starts.
3. In review mode, restack the children now: `gt sync --no-interactive --delete-all && gt submit --stack --no-interactive --no-edit --update-only` on `stacking gt`, or the manual retarget-and-rebase lifecycle in [../pipeline/delivery.md](../pipeline/delivery.md#the-stack-lifecycle). Then move to the next PR up.

Independent PRs (no shared stack) skip the restack and can be processed in any order, still one at a time.

## Verify, then stop or merge

After each PR's fixes: run the recorded tests or recipe, rerun the rendered smoke when a UI contract applies and a fix touched a rendered file, and push. Then run the confirmation pass, and wait for checks per the waiting rule in [../pipeline/merge.md](../pipeline/merge.md#waiting-is-not-blocked). A finding fixed but never verified is not fixed.

**The wait covers CI and test checks only.** Review-bot check runs on the PR (Cursor Bugbot, security review) are covered by the source decision and the confirmation pass, so none of them holds the verify row open. In merge mode, GitHub's merge API still enforces anything the repo marks as a *required* check, so a required review-bot check stays a readiness gate per [../pipeline/merge.md](../pipeline/merge.md#merging): reported if it blocks, never bypassed.

- **Review mode** ends here. The final report is one short block per PR: findings found, fixed (file and consequence each), declined (with reasons), and anything the confirmation pass left open.
- **Merge mode** continues into phase 9 **per PR**, only after that PR's review rows are complete. Merge one PR, restack, then review the next. The `review and merge` ask carried merge consent for each merge in that walk; state and log the next step (`gt merge --dry-run --no-interactive` on `stacking gt` when it applies, or the plain-language walk on manual), then run **that PR's** merge without waiting for another yes. Do not bulk-merge the stack ahead of unfinished review blocks.

## Phases

| Phase | Runs? |
|---|---|
| 0 intake | yes, lightweight. No worktree and no new branch, the PR branches exist. Ledger seeded with the mode and the stack order |
| 1 assess | no. Review track routes before the assessor; stack targets are fixed at intake |
| 2 recon | only enough to judge a finding against the code it points at |
| 3 design doc | no |
| 4 plan | no |
| 5 test-first | no, though a fix made here gets a test if the repo's conventions expect one |
| 6 implement | only the finding fixes, under the same surgical-diff rules |
| 7 verify | yes, recorded tests plus any applicable rendered smoke, per PR after its fixes |
| 8 deliver | no, the PRs exist. Fix commits push to the existing branches |
| 9 merge | merge mode only. Review mode marks the row `skip: review-only ask` |

## Consent

Invoking this track is consent to review and to push fix commits to the run's PR branches, not a waiver of the action tiers in [../SKILL.md](../SKILL.md#autonomy-host-permissions-first).

- Finding fixes, pushes to run-owned PR branches, and restacks of run-owned children are reversible-tier writes: run them, log them.
- A force push to a branch the run does not own asks individually, even for a restack.
- In merge mode, the `review and merge` ask is the merge consent: follow the merge playbook's stated-walk rules and continue to merged without re-asking.
- In review mode no merge happens, full stop. Not even for a PR that ends the review green and approved.

## The ledger is not optional here

Same reasoning as the merge track: this track changes the repo and can span sessions while checks run. One block per PR, so a context reset resumes mid-stack instead of re-reviewing from scratch:

```
- [ ] review (PR #412, base main)
  - [x] sources (head 9f3c2e1): bugbot hosted (neutral), security-review local (no run on head) (15:01)
  - [x] reviewers: bugbot 2 findings, security-review 0, thermo review 1, thermo quality 3 (15:04)
  - [x] triage: 3 in scope, 2 declined as style, 1 follow-up noted (15:12)
  - [x] implementer: one launch, 3 findings fixed across src/queue/worker.ts and src/api/webhook.ts, diff read (15:22)
  - [x] verify: pnpm vitest run green, pushed 4b7d0a8 (15:25)
  - [x] confirmation pass (head 4b7d0a8): bugbot hosted rerun no new findings, thermo quality rerun locally no new findings (15:36)
  - [x] CI checks green (15:40)
  - [~] merge: skip: review-only ask
- [ ] review (PR #413, base supercook/rate-limit-1)
```
