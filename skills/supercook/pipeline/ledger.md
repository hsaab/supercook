# The ledger

The ledger is the run's memory and its audit trail. It is the thing that makes a long run survivable: when context is compacted or a session restarts, the ledger is what tells the next turn where the work stands.

## Contents

- [Rules](#rules)
- [Format](#format)
- [Row states](#row-states)
- [Resuming](#resuming)
- [What persistence does and does not cover](#what-persistence-does-and-does-not-cover)

## Rules

1. **The parent is the only writer.** Agents return terse text and the parent records it. Concurrent writers clobber audit trails.
2. **Write at every phase transition.** A timestamp and a one-line outcome per phase, and a log row for every agent launch and return.
3. **Mutable, never lossy.** Rows get appended and checked. They never get deleted or quietly edited away.
4. **No silent skips.** Work that is not done gets `skip: <reason>`. An unexplained missing row is a defect.
5. **Plain language, no em dashes.** Every row names files and real consequences, the same as any other output.

## Format

```markdown
# Ledger: add rate limiting to public API
run-id: 2026-07-29-rate-limit-a4f2
repo: git@github.com:acme/api.git | branch: supercook/rate-limit | worktree: ~/wt/api-rate-limit
started: 2026-07-29 09:12 | tier: complex | track: feature | design doc: lite (approved 09:41)
capabilities: git yes | host github (gh authed) | worktrees yes | tests `pnpm vitest run` | PRs yes
models: arena-b gpt-5.6-sol-max ok | arena-c claude-opus-5-thinking-high ok | rest inherit
test-paths: **/*.test.ts
done: every public route rejects a 101st request in a minute with a 429, and the suite is green

## Phases
- [x] intake: worktree created, capabilities probed, ledger seeded (09:12)
- [x] assess: complex/feature, big-change flag (09:14)
- [x] recon: 3 explorers, pointers in log (09:22)
- [x] design doc (lite): design-doc.md approved (09:41)
- [x] plan: cook-off ran, plan-judge merged candidates A and C (09:55)
- [x] test-first: 6 journeys designed, slice 1 suite committed red (09:58)
- [ ] implement
  - [x] slice 1: middleware skeleton + config type (10:04, 214 reviewable / 231 raw, PR #241)
  - [ ] slice 2: redis token bucket (running: 180 reviewable)
  - [~] slice 3: admin bypass. skip: out of plan scope, filed as follow-up
- [ ] verify
- [ ] deliver

## Playbook steps (feature)
- [x] data shape named before logic: RateLimitConfig in src/rate-limit/types.ts
- [ ] journeys tested before implementation
- [ ] no opportunistic refactors in the diff

## Log
- 09:14 assessor: 3 services touched, session token shape changes, so architecture needs sign-off
- 09:22 explorers returned pointers, test command is `pnpm vitest run`
- 09:55 plan summary sent to user, continuing into implementation without waiting
- 10:11 guard: implementer modified src/rate-limit/bucket.test.ts, restored it, routed the
  concern to test-designer as an amendment
- 10:19 course-correction: spent two attempts debugging a redis mock that no open row needed,
  re-anchored to slice 2
```

## Row states

| Marker | Meaning |
|---|---|
| `[ ]` | Open. The run is not finished while any of these exist. |
| `[x]` | Done, with a timestamp and a one-line outcome. |
| `[~]` | Skipped, with `skip: <reason>` on the same line. |
| `[!]` | Blocked, with the blocker and what would unblock it. |

A blocked row still counts as open unless the blocker is a sanctioned pause, in which case say which one.

## Resuming

A new, resumed, or compacted session starts here.

A fresh session does not know the run-id yet, so matching happens in this order:

1. **Find candidates.** `.supercook/*/ledger.md` in the current tree. Also check the system temp dir, since a git-less run keeps its folder there. On the investigation track there is nothing to find, by design.
2. **Filter to this repo and branch**, read from each candidate's header. Those two are knowable without a run-id, which is what makes them the filter.
3. **Exactly one candidate with open rows**: resume it. Log its run-id so the rest of the session refers to that run and not another.
4. **More than one**: list them with their run-ids, branches, and first open rows, and ask which to resume. This is a sanctioned pause. Never break the tie by picking the newest file, which is exactly how a parallel run gets hijacked.
5. **None**: this is a new run. Go to [intake.md](intake.md).

The run-id is what identifies a run once you have one, and what every later ledger row and PR reference points at. It is not the search key on a cold start, because nothing has told you it yet.

## What persistence does and does not cover

Be honest about this, because overclaiming it leads to lost work.

**It covers**: context resets, compaction, and brand new sessions, in the same checkout.

**It does not cover**: a cloud VM, another machine, or a fresh clone. The run folder is untracked, so it does not travel.

For a run that must survive those, two options, both opt-in and both logged:

- **Commit the ledger** on the working branch, accepting the branch noise.
- **End with a handoff payload**: the header, the open rows, and the next action, written out so it can be pasted into the next session.
