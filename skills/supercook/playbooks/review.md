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
- [ ] per PR: check out the branch, launch bugbot, security-review, and both thermo reviewers in parallel, scoped to this PR's base
- [ ] per PR: dedupe and triage findings; fix real in-scope ones as one-commit diffs, decline the rest with a stated reason
- [ ] per PR: one confirmation pass on the reviewers whose findings were implemented
- [ ] per PR: run the recorded tests (and rendered smoke on a UI contract), push, wait for checks
- [ ] stack only: restack children after fixes land on a base slice, gt or manual per the ledger's stacking capability
- [ ] merge mode only: continue into phase 9 with its consent rules, one merge row per PR
- [ ] review mode only: report the per-PR findings summary and stop at open PRs
```

## The reviewer fan-out

Four reviewers per PR, launched in parallel in one message, each with a fresh context. These are host subagents with their own fixed contracts, not supercook agents, but they still take a model from the roster: pass the resolved `reviewer` slug from [../models.md](../models.md) on all four launches, including the confirmation pass. `inherit` means omit the model field, same as every other role.

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

**Fixes are delegated to `supercook-implementer` on the `review-implementer` model.** Launch it per the contract in [../agents.md](../agents.md): the objective is the triaged findings to fix, the scope list is the files those findings name, and the boundaries are unchanged (never a test file, never a path outside the scope list). The parent keeps triage, declines, the confirmation-pass decision, and the review of the returned diff. Small single-file fixes may be made inline by the parent instead, but a launch that does happen uses this role's model.

Every fix is still a diff under the normal rules: change only what the finding needs, no opportunistic cleanup, one commit per atomic change, and an explanation naming the file and the real consequence. Record each decline in the ledger and in the PR (a comment or the findings summary), so the judgment survives a context reset.

## One confirmation pass, not a loop

After fixes land, re-run only the reviewers whose findings were implemented, once, with the same scoped prompt. New findings from that pass get triaged the same way, but there is no third pass: anything still open after the confirmation pass is reported on the PR rather than looped on. Reviewers can disagree with each other's fixes forever, and this cap is what keeps a review from becoming a bot argument.

## Order on a stack

Bottom-up, one PR at a time. Fixes pushed to a base slice change what every child sits on, so a child reviewed before its parent settles gets reviewed against code that is about to move.

1. Review, fix, and verify the bottom open PR.
2. In merge mode, merge it per phase 9, which restacks the children as part of the walk.
3. In review mode, restack the children now: `gt sync --no-interactive --delete-all && gt submit --stack --no-interactive --no-edit --update-only` on `stacking gt`, or the manual retarget-and-rebase lifecycle in [../pipeline/delivery.md](../pipeline/delivery.md#the-stack-lifecycle). Then move to the next PR up.

Independent PRs (no shared stack) skip the restack and can be processed in any order, still one at a time.

## Verify, then stop or merge

After each PR's fixes: run the recorded tests or recipe, rerun the rendered smoke when a UI contract applies and a fix touched a rendered file, push, and wait for checks per the waiting rule in [../pipeline/merge.md](../pipeline/merge.md#waiting-is-not-blocked). A finding fixed but never verified is not fixed.

- **Review mode** ends here. The final report is one short block per PR: findings found, fixed (file and consequence each), declined (with reasons), and anything the confirmation pass left open.
- **Merge mode** continues into phase 9 exactly as the merge playbook specifies, including its consent rules: `gt merge --dry-run --no-interactive` as the batched-consent statement on `stacking gt`, the plain-language sequence on manual, and individual asks outside a batch. The merge itself is irreversible and always asks.

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
- Merges follow the merge playbook's rules unchanged: ask per PR, or one batched yes for a stated stack walk.
- In review mode no merge happens, full stop. Not even for a PR that ends the review green and approved.

## The ledger is not optional here

Same reasoning as the merge track: this track changes the repo and can span sessions while checks run. One block per PR, so a context reset resumes mid-stack instead of re-reviewing from scratch:

```
- [ ] review (PR #412, base main)
  - [x] reviewers: bugbot 2 findings, security-review 0, thermo review 1, thermo quality 3 (15:04)
  - [x] triage: 3 fixed, 2 declined as style, 1 follow-up noted (15:22)
  - [x] confirmation pass: bugbot and thermo quality rerun, no new findings (15:31)
  - [x] verify: pnpm vitest run green, pushed, checks green (15:40)
  - [~] merge: skip: review-only ask
- [ ] review (PR #413, base supercook/rate-limit-1)
```
