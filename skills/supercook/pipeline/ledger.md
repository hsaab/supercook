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
6. **A roster row closes on a launch record or an `inline` record.** The assess, recon, plan, test-first, implement, and verify rows name their worker from the moment they are seeded. Each one is checked only when the row or its log line says which worker ran, through which spawn path, and on which model actually used (`supercook-implementer via Task, composer-2.5`, or `inherit` when the model field was dropped), or says `inline` with the reason (`spawn none`, or the launch error quoted after the retry ladder in [SKILL.md](../SKILL.md#start-here-the-launch-rule)). The older `degraded: parent inline (spawn none)` still counts. That holds at every tier, trivial included. A roster row checked with none of these is a silent skip, even when the work itself is good. Solo mode is in [agents.md](../agents.md#no-spawn-tool-run-roles-inline).

### Invalid skip reasons

These reasons are never valid on **standard** or **complex** tier unless assessor already returned **trivial** and tier collapse applies:

| Reason (or close variant) | Why invalid |
|---|---|
| `user checklist` / `coordinator spec` | A pasted task list is not assessor, recon, or `plan.md`. |
| `agents not installed` | Each role still runs through a spawn tool or, with `spawn: none`, inline in the parent; see [../agents.md](../agents.md#spawn-paths-when-typed-agents-are-missing). |
| `plan in kickoff` | Spec pointers do not replace planner or arena output. |
| `worker assignment` | Project and cloud briefs still run the pipeline. |
| `faster inline` / `small task` / `assessor already launched` | Never a reason for the parent to do a roster phase, at any tier. Size is the assessor's verdict, and a trivial verdict removes phases, not workers. |

Valid skips cite assessor verdict, user-selected track, tier collapse, big-change off, or an explicit scope modifier from [../SKILL.md](../SKILL.md).

A `[~]` skip removes a phase from the roster. It does not reopen that work on the parent while the row stays skipped. Solo parent work is valid only when rule 6 closes the row with an `inline` record on a checked row (`spawn none`, a quoted launch error after the retry ladder, or the older `degraded: parent inline (spawn none)` wording).

## Format

```markdown
# Ledger: add rate limiting to public API
run-id: 2026-07-29-rate-limit-a4f2
repo: git@github.com:acme/api.git | branch: supercook/rate-limit | worktree: ~/wt/api-rate-limit
started: 2026-07-29 09:12 | tier: complex | track: feature | design doc: lite (approved 09:41)
capabilities: git yes | host github (gh authed) | worktrees yes | tests `pnpm vitest run` | PRs yes | stacking gt | supercook-agents installed | spawn typed | parent-host cursor-chat
models: standard grok-4.7-high | arena-a grok-4.7-high | arena-b composer-2.5 | arena-c grok-4.7-high | plan-judge grok-4.7-high | plan-optimizer grok-4.7-medium | implementer composer-2.5 | explorer composer-2.5 | reviewer grok-4.7-high | review-implementer composer-2.5
test-paths: **/*.test.ts
ui-change: no | ui-source: none | render-check: none
done: every public route rejects a 101st request in a minute with a 429, and the suite is green

## Phases
- [x] intake: worktree created, capabilities probed, ledger seeded (09:12)
- [x] assess: supercook-assessor (typed) returned complex/feature, big-change flag (09:14)
- [x] recon: 3 supercook-explorer launches (typed), pointers in log (09:22)
- [x] design doc (lite): design-doc.md approved (09:41)
- [x] plan: 3 supercook-arena-runner launches, supercook-plan-judge merged candidates A and C (09:55)
- [x] test-first: supercook-test-designer (typed) designed 6 journeys, slice 1 suite committed red (09:58)
- [ ] implement: supercook-implementer, one launch per slice
  - [x] slice 1: middleware skeleton + config type (typed launch, 10:04, 214 reviewable / 231 raw, PR #241)
  - [ ] slice 2: redis token bucket (running: 180 reviewable)
  - [~] slice 3: admin bypass. skip: out of plan scope, filed as follow-up
- [ ] verify: supercook-verifier, fresh launch per slice
- [ ] deliver
- [~] merge. skip: no merge asked for, run ends at the open PRs

## Playbook steps (feature)
- [x] data shape named before logic: RateLimitConfig in src/rate-limit/types.ts
- [ ] journeys tested before implementation
- [ ] no opportunistic refactors in the diff

## Log
- 09:14 assessor (grok-4.7-high): 3 services touched, session token shape changes, so architecture needs sign-off
- 09:22 explorer (composer-2.5): returned pointers, test command is `pnpm vitest run`
- 09:55 plan summary sent to user, continuing into implementation without waiting
- 10:11 guard: implementer modified src/rate-limit/bucket.test.ts, restored it, routed the
  concern to test-designer as an amendment
- 10:19 course-correction: spent two attempts debugging a redis mock that no open row needed,
  re-anchored to slice 2
```

For a contract-level UI run, the same header and phase list include:

```markdown
ui-change: yes | ui-source: figma https://figma.com/design/example?node-id=26-2
render-check: browser

- [ ] verify
  - [x] structural UI-1: verifier returned ui-contract ok (10:31)
  - [ ] rendered smoke UI-1: /insights/analyst at 1440x900 and 900x900, record head SHA
  - [ ] rendered smoke composed: /insights/analyst with dashboard and rail

## Log
- 09:26 UI source resolved: Figma node 26:2, screenshot retained in run artifacts,
  semantic order copied into plan.md
- 09:45 UI deviation approved: Open workflow stays static because community users
  cannot enter licensed Insights
```

An open-pr run also records its pre-write scope baseline:

```markdown
open-pr scope: task <quoted task> | base <sha> | head <sha>
- existing path: src/report.ts | purpose: add CSV export
- retrospective test: src/report.test.ts | purpose: pin the supplied UI contract
verification recipe: verification-report.md | sha256 <digest>
```

## Row states

| Marker | Meaning |
|---|---|
| `[ ]` | Open. The run is not finished while any of these exist. |
| `[x]` | Done, with a timestamp and a one-line outcome. |
| `[~]` | Skipped, with `skip: <reason>` on the same line. |
| `[!]` | Blocked, with the blocker and what would unblock it. |

A blocked row still counts as open unless the blocker is a sanctioned pause, in which case say which one.

A rendered-smoke row can be `[!]` only when no renderer can load the target. Name
the route, attempted command, manual checks, and the user's answer. That
sanctioned-blocked row may proceed to delivery with the missing evidence disclosed,
but it never means visually verified. A route that rendered incorrectly is a
failure gap, not a sanctioned block.

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

- **Commit the ledger** on the working branch, accepting the branch noise. Ask for this up front with `/supercook keep ledger <task>`.
- **End with a handoff payload**: the header, the open rows, and the next action, written out so it can be pasted into the next session.
