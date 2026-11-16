# The ledger

The ledger is the run's memory. When context is compacted or a session restarts, it tells the next turn where the work stands. Only you write it; workers return text and you record it. The investigation track has no ledger: the todo list is the record and nothing is written to the repo.

## Seed

1. **Pick the tree** before creating any file. On a clean tree on a sensible base, work in place on a new `supercook/<slug>` branch. With unrelated uncommitted work, use a worktree, and never stash or commit someone else's work:
   `git worktree add ../<repo>-<slug> -b supercook/<slug> origin/<default-branch>`
   merge and review check out the existing PR branch instead (`gh pr checkout <n>`).
2. **Make the run folder** `.supercook/<run-id>/`, with run-id `<YYYY-MM-DD>-<slug>-<4 random chars>`, and keep it out of git without touching `.gitignore`:
   ```bash
   EXCLUDE=$(git rev-parse --git-path info/exclude)
   grep -qxF '.supercook/' "$EXCLUDE" 2>/dev/null || printf '\n.supercook/\n' >> "$EXCLUDE"
   ```
   `--git-path` matters because a linked worktree's `.git` is a file. Without git, use the system temp dir. A rule against committing logs does not skip this; the folder is untracked.
3. **Point at it**: write `.supercook/active-run` with the ledger's relative path, and delete it when the run ends.
4. **Pin the inputs.** Acceptance criteria from the task or its ticket go verbatim to `acceptance.md`, numbered `AC-1` onward. A supplied plan goes verbatim to `user-plan.md`. An unreadable ticket is the missing-access pause.
5. **Write `ledger.md`**: the header, then the playbook's steps copied verbatim under `## Steps`, with tier skips marked. A slice block goes in once as slice 1; when `plan.md` lands, add one block per further slice. With no plan, the task is slice 1.

```markdown
# Ledger: add rate limiting to public API
run-id: 2026-07-29-rate-limit-a4f2 | repo: git@github.com:acme/api.git | branch: supercook/rate-limit
supercook: 0.6.0 from ~/.cursor/plugins/local/supercook
tier: complex | track: feature | big-change: yes
spawn: typed | tests: `pnpm vitest run` | test-paths: **/*.test.ts
models: standard grok-4.7-high | arena-a grok-4.7-high | arena-b composer-2.5 | arena-c grok-4.7-high | plan-judge grok-4.7-high | implementer composer-2.5 | explorer composer-2.5 | reviewer grok-4.7-high | review-implementer composer-2.5
done: every public route answers a 101st request in one minute with a 429, and the suite is green

## Steps
- [x] map the code the feature touches: supercook-explorer, a broad launch then one per area (3 launches via Task, composer-2.5, 09:22)
- [x] design doc, big-change only (lite, approved 09:41)
- [x] plan.md names the data shape and the user journeys: three supercook-arena-runner launches then supercook-plan-judge (4 launches via Task, 10:02)
- [ ] each slice in plan order, closed before the next starts (yours)
  - [x] slice 1 journey tests land red before the code: supercook-test-designer (Task, grok-4.7-high, tests 3c1d9e0)
  - [x] slice 1 code, middleware skeleton: supercook-implementer (Task, composer-2.5, 214 reviewable / 231 raw)
  - [x] slice 1 matches its plan rows: supercook-verifier (Task, grok-4.7-high, verdict: pass)
  - [x] slice 1 PR opens (PR #241)
  - [ ] slice 2 journey tests land red before the code, redis token bucket: supercook-test-designer

## Log
- 09:14 assess: tier: complex | track: feature | big-change: yes | why: three services change and so does the session token shape
- 10:11 check: the implementer edited src/rate-limit/bucket.test.ts; restored it and sent the concern to the test designer
```

`spawn` is `typed`, `generalPurpose`, another tool's name, or `none`. The test command and test paths come from the first explorer, with evidence. `models:` lists every roster key, resolved once per [../models.md](../models.md); write `inherit` for every role when the spawn tool has no model field.

## Rows

| Marker | Meaning |
|---|---|
| `[ ]` | Open. The run is not finished while any exist. |
| `[x]` | Done, with the time and a one-line outcome. |
| `[~]` | Skipped, with `skip: <reason>` on the line. |
| `[!]` | Blocked, naming the blocker. Counts as open unless it is a sanctioned pause. |

- A worker step closes only with its launch record (spawn path and the model actually used) or `inline (<reason>)`. A checked worker step with neither is a silent skip.
- A skip cites the tier, the track, `big-change: no`, or a scope modifier. Size, speed, a pasted checklist, a plan in the kickoff, or agents not being installed never skip a worker step.
- Rows are appended and checked, never deleted. Log every launch and return, every check that fired, and every course correction.

## Resume

1. Find `.supercook/*/ledger.md` in the tree, plus the temp dir for a git-less run.
2. Keep the ones whose header matches this repo and branch.
3. One with open steps: resume it and log its run-id. Several: list them and ask (a sanctioned pause); never pick the newest. None: start a new run.

The run folder is untracked, so it survives compaction and new sessions in the same checkout, not another machine. `keep ledger` commits it on the branch; otherwise end with a handoff: the header, the open steps, and the next action.
