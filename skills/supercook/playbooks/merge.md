# Playbook: merge

A PR already exists. Drive it to merged.

## Trigger and entry

**Trigger: an explicit merge ask, whenever it arrives.** In the invocation (`/supercook merge PR 412`), mid-run after the user sees the PR, or cold on a PR from last week. Nothing else selects this track. The assessor never routes here on its own, and phase 8 still ends a normal run at an open PR.

**Entry: continue a run if one exists, otherwise open one.**

- **The ask lands inside a live run.** Phase 9 is that run's tail. Reuse the existing ledger and the stack context phase 8 just built. No new run, no second ledger.
- **The ask arrives cold.** Intake seeds a run on this track around the target PR, then jump to phase 9.

Everything after entry is the same loop in [../pipeline/merge.md](../pipeline/merge.md), reading the same `gh pr view` state. A PR that needs conflict resolution, a CI fix, and a stack walk gets all three without this playbook anticipating that combination.

On cold entry, recover any UI source, contract ids, approved deviations, contract
summary, full smoke target, tested head SHA, and latest result from the PR body. The
run ledger may be untracked and unavailable. Never invent a design from the diff.

## Steps

Copy these into the ledger verbatim.

```
- [ ] stack only: confirm branches are gt-tracked when stacking gt (else fall back to manual); state and log the full merge sequence (gt merge --dry-run --no-interactive when stacking gt, else plain-language walk); add one merge row per PR
- [ ] read the PR state: mergeable, checks, reviews, base drift
- [ ] resolve conflicts, understanding both sides
- [ ] triage every comment, fix or answer each one
- [ ] fix in-scope CI failures, report out-of-scope ones
- [ ] UI contract only: confirm current rendered-smoke evidence
- [ ] merge with the repo's default method (gt merge --no-interactive when stacking gt, else gh pr merge)
- [ ] handle children if this is a stack (gt sync --no-interactive --delete-all && gt submit --stack --no-interactive --no-edit --update-only when stacking gt, else the manual restack in delivery.md); before gt sync, confirm no stack sibling is checked out in another worktree
```

## Phases

| Phase | Runs? |
|---|---|
| 0 intake | yes, lightweight. No worktree and no new branch, since the PR's branch already exists. A ledger is still seeded |
| 1 assess | only to confirm the target PR and whether it is part of a stack |
| 2 recon | only enough to understand code a comment or a CI failure points at |
| 3 design doc | no |
| 4 plan | no |
| 5 test-first | no, though a fix made here gets a test if the repo's conventions expect one |
| 6 implement | only the fixes the loop demands, under the same surgical-diff rules |
| 7 verify | run the recorded tests or recipe before merging, same gate as anywhere else |
| 8 deliver | no, the PR exists |
| 9 merge | yes, this is the whole job |

## The ledger is not optional here

A PR stuck on broken CI is a long-running job, and that is what the ledger exists for. Seed `.supercook/<run-id>/ledger.md` at intake with one row per loop concern, per [../pipeline/ledger.md](../pipeline/ledger.md).

This is the opposite of the investigation track, which writes nothing. The difference is that this track changes the repo and can span sessions, so the record has to survive a context reset. Without it, a resumed session re-derives the PR's state from scratch and loses every judgment call already made about a comment or a flaky check.

## Consent

The merge ask that selected this track is the consent to merge. Do not ask again before `gh pr merge` or `gt merge`; state what is about to happen, log it, and run it until the work is merged. What the ask does not waive is the rest of the action tiers in [../SKILL.md](../SKILL.md#autonomy-host-permissions-first): host approval prompts, and writes outside the stated scope.

- **Single PR**: state the merge in a progress note and a ledger row, then run `gh pr merge` (or `gt merge` for one branch) without waiting.
- **Stack with `stacking gt`**: confirm the tip branch appears in `gt log` (tracked). If it does not, `gt track --force --no-interactive` only when the parent bases are clear, otherwise walk this stack on the manual path. Run `gt merge --dry-run --no-interactive`, log that list as the sequence, then `gt merge --no-interactive` followed by `gt sync --no-interactive --delete-all && gt submit --stack --no-interactive --no-edit --update-only`. A surprise (`gt merge` failure, new conflict, red required check, comment demanding a code change, restack that does not apply cleanly, sibling checked out in another worktree) gets handled, the updated sequence gets logged, and the walk continues.
- **Stack with `stacking manual`**: state and log the full sequence up front (every merge, every expected rebase and force push, in order), then run the whole walk. Same handle-log-continue rule on surprises. Mechanics in [../pipeline/merge.md](../pipeline/merge.md#stacked-prs).
- A force push to a branch that is not run-owned and not part of the stated walk still asks individually. The merge ask covers the rewrites the walk requires, not unrelated branches. `gt submit` on run-owned stack branches follows the reversible tier in [../SKILL.md](../SKILL.md#autonomy-host-permissions-first).
- Branch protection, a missing required approval, and a failing required check get reported. They are never bypassed. GitHub still enforces them under both `gt merge` and `gh pr merge`, and they are the only things that stop a merge-ask run short of merged.

## Fixes made here are still diffs

A CI fix or a review fix obeys every rule a normal implementation phase obeys: change only what the failure needs, no opportunistic cleanup, name the file and the real consequence in the explanation, and one commit per atomic change.

If a comment asks for something that turns out to be a feature rather than a fix, that is a new run on a different track. Say so, note it as a follow-up, and keep it out of this diff.

When a UI contract applies, require current rendered-smoke evidence before merge.
Rerun it when a merge-track fix changed the UI or when the recorded smoke predates
the current head. If the PR body does not carry enough contract detail, ask for the
source or manual confirmation and log the sanctioned pause. A structural suite
cannot substitute for the missing rendered check.
