# Playbook: review

Slice PRs exist. Run the external reviewers on each one, implement the real findings, and merge only when the ask included it.

## Trigger and entry

**Trigger: an explicit review ask, whenever it arrives.** `/supercook review`, `/supercook review PR 412`, or `/supercook review and merge`, in the invocation or mid-run after phase 8 opened the slice PRs. Nothing else selects this track. The assessor never routes here on its own.

**The ask decides the mode, and the mode is fixed at intake.**

- `review`: review, fix, verify, and stop at healthy open PRs with a findings summary per PR.
- `review and merge`: the same work, then continue into phase 9 per [merge.md](merge.md) and [../pipeline/merge.md](../pipeline/merge.md).

A clean review never upgrades itself into a merge. Record `mode: review` or `mode: review+merge` in the ledger header so a resumed session cannot guess wrong. Record the two resolved model slugs beside it (`models: reviewer <slug or inherit> | review-implementer <slug or inherit>`), resolved once at intake per [../models.md](../models.md), so a resume launches with the same models instead of re-resolving.

**Entry: continue a run if one exists, otherwise open one.**

- **The ask lands inside a live run.** Reuse the existing ledger and the stack context phase 8 just built. No new run, no second ledger.
- **The ask arrives cold.** Intake seeds a run on this track around the target PRs. Targets are the named PRs, or the current branch's PR plus every open PR stacked on it. Record the stack order and each PR's base branch in the ledger before reviewing anything.

Stacking mechanics follow the `stacking gt | manual` capability intake records. On cold entry apply the same tracked-branch check as the merge track: `stacking gt` only counts for a stack whose branches appear in `gt log`, with `gt track --force --no-interactive` allowed when the parent bases are clear, otherwise this stack walks the manual path.

## Steps

Copy these into the ledger verbatim.

```
- [ ] resolve targets: named PRs or the current branch's PR and its stack; record bottom-up order and each PR's base
- [ ] per PR: check out the branch; record each of bugbot and security-review as `hosted` (already ran on the PR head) or `local`
- [ ] per PR: launch both thermo reviewers plus every `local` reviewer in parallel, scoped to this PR's base; collect `hosted` findings from the PR
- [ ] per PR: dedupe and triage findings; decline the rest with a stated reason
- [ ] per PR: one supercook-implementer launch (review-implementer model) fixes all in-scope findings as one-commit diffs
- [ ] per PR: one confirmation pass on the reviewers whose findings were implemented: `local` ones rerun locally, `hosted` ones are read from their rerun on the pushed head
- [ ] per PR: run the recorded tests (and rendered smoke on a UI contract), push, wait for CI checks plus any `hosted` confirmation run; never wait on a review-bot check whose reviewer ran locally
- [ ] stack only: restack children after fixes land on a base slice, gt or manual per the ledger's stacking capability
- [ ] merge mode only: continue into phase 9 under the merge ask already given, one merge row per PR
- [ ] review mode only: report the per-PR findings summary and stop at open PRs
```

## Reuse hosted Bugbot and security review

Bugbot and security review often already ran on the PR as hosted review bots. When they did, their findings are the review: read them from the PR instead of paying for the same review twice. The thermo reviewers have no hosted form and always run locally.

Decide per reviewer, before the fan-out, against the PR's current head commit:

```bash
gh pr view <n> --json headRefOid --jq .headRefOid
gh api repos/{owner}/{repo}/commits/<head-sha>/check-runs \
  --jq '.check_runs[] | {name, status, conclusion, html_url}'
```

- **A completed check run for that reviewer on the head SHA** (Bugbot's is named like `Cursor Bugbot`; match security review by its check name the same way): source is `hosted`. Collect its findings from the check run output and the bot's review comments and review bodies on the PR (`gh api repos/{owner}/{repo}/pulls/<n>/comments`, `gh pr view <n> --json reviews`). Skip comments on outdated diffs or threads already resolved.
- **A run queued or in progress on the head SHA**: wait for it per [../pipeline/merge.md](../pipeline/merge.md#waiting-is-not-blocked), then treat it as `hosted`. Launching a local duplicate while it runs wastes the batch.
- **No run on the head SHA** (never ran, not installed on the repo, or only ran on an older commit): source is `local`. A run on an older commit missed the code pushed since, so it does not count.
- **A run that failed or errored without findings**: source is `local`. A crashed bot is not a clean review.

Record the source and the head SHA it was judged against in the ledger. Hosted findings go through the same dedupe and triage as local ones; being on the PR earns them no extra trust.

## The reviewer fan-out

Up to four reviewers per PR, launched in parallel in one message, each with a fresh context: both thermo reviewers always, plus `bugbot` and `security-review` when their source is `local`. These are host subagents with their own fixed contracts, not supercook agents, but they still take a model from the roster: pass the resolved `reviewer` slug from [../models.md](../models.md) on every launch, including the confirmation pass. `inherit` means omit the model field, same as every other role. A `hosted` reviewer runs on its own service, so no model applies.

**Parallel means one batch, without exception.** All local reviewer launches go out as a single batch of Task calls. Never launch one reviewer, wait for it, then launch the next; none of them depends on another's output, so a sequential fan-out multiplies the wall time for nothing. The confirmation pass follows the same rule: every reviewer being rerun locally launches in one batch. Parallelism stays within one PR because the diff-computing reviewers read the checked-out working tree and only one PR branch can be checked out at a time, so it is one PR at a time, all local reviewers at once within it.

First check out the PR's branch (`gh pr checkout <n>`), because the diff-computing reviewers read the working tree.

**`bugbot`** and **`security-review`** compute the diff themselves from the repository path. Launch each with exactly this prompt shape:

```
Full Repository Path: <absolute path to this run's working tree>
Diff: branch changes
Base Branch: <this PR's base branch>
```

**`Base Branch` is what scopes a stacked slice.** A child PR's base is the previous slice's branch, not the default branch. Omitting it makes every reviewer see the whole stack's diff and report the parent slices' code as this PR's, so the findings land on the wrong PR.

**`thermo-nuclear-review-subagent`** and **`thermo-nuclear-code-quality-review-subagent`** do not compute the diff. Gather it first (`git diff <base-branch>...HEAD` plus the full contents of the changed files that need context) and pass it in the prompt, asking each for prioritized findings with file references and evidence.

**When a reviewer subagent is not installed on this host**, run the ones that exist, and record the gap as a ledger row and one line in the findings summary. Never fabricate a review, and never substitute a generic agent pretending to be one.

## Triage before implementing

Dedupe findings across the four reviewers first: overlapping findings merge into one entry and carry more weight. Then triage each finding with the same skeptical-bot rule as [../pipeline/merge.md](../pipeline/merge.md#comment-triage). Reviewers are useful and also confidently wrong sometimes, so verify every claim against the actual code before acting on it.

- **A real bug or a correct concern**: fix it on this PR's branch.
- **A style preference the repo does not enforce**: decline, with the reason recorded.
- **Wrong about the code**: decline, naming the file and line that disproves it.
- **Out of scope for this slice**: note it as a follow-up, keep it out of this diff.

**Fixes always run in a subagent: one `supercook-implementer` launch per PR, on the `review-implementer` model.** The parent never edits source inline, not even for a one-line finding; the subagent is what keeps the fix on the right model with a clean context. Launch after all four reviewers have returned and triage is done, per the contract in [../agents.md](../agents.md), carrying:

- the full deduped in-scope findings list, one entry per finding with the file, the claim, and the evidence that survived triage
- the scope list: the union of files those findings name
- the PR's recorded test command as the verification

Boundaries are unchanged: never a test file, never a path outside the scope list. The parent keeps triage, declines, the confirmation-pass decision, and reads the returned diff itself before committing. If the confirmation pass produces new in-scope findings, that is a second implementer launch for this PR (still capped by the no-third-pass rule), not an inline patch.

Every fix is still a diff under the normal rules: change only what the finding needs, no opportunistic cleanup, one commit per atomic change, and an explanation naming the file and the real consequence. Record each decline in the ledger and in the PR (a comment or the findings summary), so the judgment survives a context reset.

## One confirmation pass, not a loop

After fixes land, re-run only the reviewers whose findings were implemented, once. A `local` reviewer reruns locally with the same scoped prompt. A `hosted` reviewer confirms through its own rerun on the pushed head: wait for that check run during verify and read its new findings. If no hosted run appears on the new head by the time the CI checks finish, run that reviewer locally instead, so a confirmation pass never silently goes missing. New findings from that pass get triaged the same way, but there is no third pass: anything still open after the confirmation pass is reported on the PR rather than looped on. Reviewers can disagree with each other's fixes forever, and this cap is what keeps a review from becoming a bot argument.

## Order on a stack

Bottom-up, one PR at a time. Fixes pushed to a base slice change what every child sits on, so a child reviewed before its parent settles gets reviewed against code that is about to move.

1. Review, fix, and verify the bottom open PR.
2. In merge mode, merge it per phase 9, which restacks the children as part of the walk.
3. In review mode, restack the children now: `gt sync --no-interactive --delete-all && gt submit --stack --no-interactive --no-edit --update-only` on `stacking gt`, or the manual retarget-and-rebase lifecycle in [../pipeline/delivery.md](../pipeline/delivery.md#the-stack-lifecycle). Then move to the next PR up.

Independent PRs (no shared stack) skip the restack and can be processed in any order, still one at a time.

## Verify, then stop or merge

After each PR's fixes: run the recorded tests or recipe, rerun the rendered smoke when a UI contract applies and a fix touched a rendered file, push, and wait for checks per the waiting rule in [../pipeline/merge.md](../pipeline/merge.md#waiting-is-not-blocked). A finding fixed but never verified is not fixed.

**The wait covers CI and test checks, plus hosted confirmation runs.** A review-bot check (Cursor Bugbot, security review) holds the verify row open only when that reviewer's source is `hosted` and its findings were implemented, because its rerun is the confirmation pass. A review-bot check whose reviewer ran locally is replaced by the local fan-out; pending or absent, it never holds the verify row open. In merge mode, GitHub's merge API still enforces anything the repo marks as a *required* check, so a required review-bot check stays a readiness gate per [../pipeline/merge.md](../pipeline/merge.md#merging): reported if it blocks, never bypassed.

- **Review mode** ends here. The final report is one short block per PR: findings found, fixed (file and consequence each), declined (with reasons), and anything the confirmation pass left open.
- **Merge mode** continues into phase 9 exactly as the merge playbook specifies. The `review and merge` ask already carried the merge consent: state and log the sequence (`gt merge --dry-run --no-interactive` on `stacking gt`, the plain-language walk on manual), then run it to merged without waiting for another yes.

## Phases

| Phase | Runs? |
|---|---|
| 0 intake | yes, lightweight. No worktree and no new branch, the PR branches exist. Ledger seeded with the mode and the stack order |
| 1 assess | only to confirm the target PRs and their stack relationship |
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
  - [x] sources (head 9f3c2e1): bugbot hosted, security-review local (no run on head) (15:01)
  - [x] reviewers: bugbot 2 findings (hosted), security-review 0, thermo review 1, thermo quality 3 (15:04)
  - [x] triage: 3 in scope, 2 declined as style, 1 follow-up noted (15:12)
  - [x] implementer: one launch, 3 findings fixed across src/queue/worker.ts and src/api/webhook.ts, diff read (15:22)
  - [x] confirmation pass: thermo quality rerun locally, no new findings; bugbot confirms through its hosted rerun after push (15:31)
  - [x] verify: pnpm vitest run green, pushed 4b7d0a8, CI checks green, hosted bugbot rerun on 4b7d0a8 no new findings (security-review check skipped, ran locally) (15:40)
  - [~] merge: skip: review-only ask
- [ ] review (PR #413, base supercook/rate-limit-1)
```
