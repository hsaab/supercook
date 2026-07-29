# Playbook: merge

A PR already exists. Drive it to merged.

## Trigger and entry

**Trigger: an explicit merge ask, whenever it arrives.** In the invocation (`/supercook merge PR 412`), mid-run after the user sees the PR, or cold on a PR from last week. Nothing else selects this track. The assessor never routes here on its own, and phase 8 still ends a normal run at an open PR.

**Entry: continue a run if one exists, otherwise open one.**

- **The ask lands inside a live run.** Phase 9 is that run's tail. Reuse the existing ledger and the stack context phase 8 just built. No new run, no second ledger.
- **The ask arrives cold.** Intake seeds a run on this track around the target PR, then jump to phase 9.

Everything after entry is the same loop in [../pipeline/merge.md](../pipeline/merge.md), reading the same `gh pr view` state. A PR that needs conflict resolution, a CI fix, and a stack walk gets all three without this playbook anticipating that combination.

## Steps

Copy these into the ledger verbatim.

```
- [ ] read the PR state: mergeable, checks, reviews, base drift
- [ ] resolve conflicts, understanding both sides
- [ ] triage every comment, fix or answer each one
- [ ] fix in-scope CI failures, report out-of-scope ones
- [ ] merge with the repo's default method
- [ ] handle children if this is a stack
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
| 7 verify | run the suite before merging, same gate as anywhere else |
| 8 deliver | no, the PR exists |
| 9 merge | yes, this is the whole job |

## The ledger is not optional here

A PR stuck on broken CI is a long-running job, and that is what the ledger exists for. Seed `.supercook/<run-id>/ledger.md` at intake with one row per loop concern, per [../pipeline/ledger.md](../pipeline/ledger.md).

This is the opposite of the investigation track, which writes nothing. The difference is that this track changes the repo and can span sessions, so the record has to survive a context reset. Without it, a resumed session re-derives the PR's state from scratch and loses every judgment call already made about a comment or a flaky check.

## Consent

Invoking this track is the consent to attempt a merge, not a waiver of the action tiers in [../SKILL.md](../SKILL.md#autonomy-host-permissions-first).

- `gh pr merge` is irreversible. Ask before running it, every time.
- `push --force-with-lease` on a stack child is irreversible. Ask before each one. Consent to merge is not consent to rewrite a branch.
- Branch protection, a missing required approval, and a failing required check get reported. They are never bypassed.

## Fixes made here are still diffs

A CI fix or a review fix obeys every rule a normal implementation phase obeys: change only what the failure needs, no opportunistic cleanup, name the file and the real consequence in the explanation, and one commit per atomic change.

If a comment asks for something that turns out to be a feature rather than a fix, that is a new run on a different track. Say so, note it as a follow-up, and keep it out of this diff.
