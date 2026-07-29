# Agent launch contracts

The eight agents live at the plugin root in `agents/`, not in this skill folder. That is where Cursor discovers them, so they show up as real delegatable subagents. Every name is prefixed `supercook-` so a public install cannot collide with someone's own `implementer` or `verifier`.

This file is the launch contract: what the parent passes in, when the job is done, what comes back, and what the parent checks afterwards. The prompt itself lives in the agent file.

## Contents

- [The roster](#the-roster)
- [What every launch includes](#what-every-launch-includes)
- [Per-role contracts](#per-role-contracts)
- [Parent-side guards](#parent-side-guards)
- [Fallback when the agents are not installed](#fallback-when-the-agents-are-not-installed)

## The roster

| Agent | Role in models.md | Writes files? | Phase |
|---|---|---|---|
| `supercook-assessor` | standard | No | 1 |
| `supercook-explorer` | explorer | No | 2 |
| `supercook-planner` | standard | `plan.md` only | 4 |
| `supercook-arena-runner` | arena-a, arena-b, arena-c | Its own candidate plan only | 4 |
| `supercook-plan-judge` | plan-judge | `plan.md` only | 4 |
| `supercook-test-designer` | standard | Test files only | 5 |
| `supercook-implementer` | implementer | Source, never tests | 6 |
| `supercook-verifier` | standard | No source edits, runs commands | 7 |

## What every launch includes

Pass these on every launch, without exception:

- **The objective**, in one sentence, specific to this run.
- **The run folder path**, so the agent can read `plan.md` and `design-doc.md` when relevant. Never ask an agent to write the ledger.
- **Its inputs**: file pointers from recon, the scope list, the test command, whatever that role needs.
- **The model**, resolved from [models.md](models.md), or nothing when the role is `inherit`.
- **The plain-language rule**: its returns must name files and real consequences, and must not contain em dashes.

Do not paste the whole conversation, prior agent output, or file contents that the agent can read itself. A clean context window is the reason to delegate at all.

## Per-role contracts

### supercook-assessor

- **Inputs**: the raw task text, the repo name, the capability probe result.
- **Effort budget**: one classification pass, under 5 tool calls. It reads enough to classify, not enough to plan.
- **Done when**: tier, track, and big-change flag are all named.
- **Returns**, exactly 4 lines:
  ```
  tier: trivial | standard | complex
  track: bugfix | feature | investigation | refactor | open-pr
  big-change: yes | no
  why: <one sentence naming what drove the verdict>
  ```

### supercook-explorer

- **Inputs**: a scoped question list. One area per launch. Launch several in parallel for a broad task.
- **Effort budget**: about 10 tool calls per launch.
- **Done when**: every question in its scope has a `file:line` pointer or an explicit "not found".
- **Returns**: pointers first, then a how-it-works note capped at 10 lines. No file dumps, no pasted implementations.
- **Also returns on the broad launch**: the repo's test path patterns and the exact command that runs the suite. Later phases depend on both.

### supercook-planner

- **Inputs**: task, tier, track, recon pointers, the Design Doc when one exists, the slice budget.
- **Effort budget**: one pass. Plan, do not explore. If it needs to explore, recon was too thin.
- **Done when**: `plan.md` exists with numbered slices, each carrying scope, a named verification, and a reviewable-line estimate.
- **Returns**: the slice list, one line each, and the total estimate.

### supercook-arena-runner

- **Inputs**: identical brief for all three, plus recon pointers. The only difference between launches is the model.
- **Effort budget**: one pass, no implementation, no file writes outside its own candidate plan.
- **Done when**: a complete candidate plan exists in its own file, with slices, risks, and the one decision it is least sure about.
- **Returns**: the approach in two sentences, the slice list with estimates, and its least-sure decision. Not the plan itself: the judge reads the candidate files directly, so returning the full plan would put three plans in the parent's context for no reason.

### supercook-plan-judge

- **Inputs**: all three candidate plans, the recon pointers, the slice budget.
- **Effort budget**: read, compare, decide, write. No new exploration.
- **Done when**: `plan.md` is written and every slice is inside the budget or carries a logged cohesion exception.
- **Judging criteria**, in order: correctness of approach, slice sizing and independence, surgical scope, risk named honestly.
- **Returns**: which plans contributed to which slices, and the strongest idea it rejected plus why.

### supercook-test-designer

- **Inputs**: the slice, the journeys it serves, the test command, the repo's test conventions from recon.
- **Effort budget**: as long as the journeys need, but no implementation.
- **Done when**: the named journeys have tests, the suite runs, and the new tests fail for the right reason (not a syntax error, not a missing import).
- **Returns**: test paths, one line per journey in plain language, the exact command, and the failure reason for each new test.
- **Owns every test edit for the whole run.** A test that needs changing comes back here, never to the implementer.

### supercook-implementer

- **Inputs**: the slice scope as an explicit file list, the data shape, the failing tests to green, the test command.
- **Effort budget**: as long as it takes to green the named tests, and not one file further.
- **Boundaries**: never edit, add, or delete a test file. Never touch a path outside the scope list. Something outside scope that looks wrong gets reported, not fixed.
- **Done when**: the named tests pass and no file outside the scope list is modified.
- **Returns**: changed paths, the command it ran with its result, and anything it wanted to change but did not.

### supercook-verifier

- **Inputs**: `plan.md`, the ledger, the diff, the test command. Fresh context only, no implementation history.
- **Effort budget**: enough to run the suite and check every plan row.
- **Done when**: every plan row is marked landed or missing with evidence, and the suite has been run in this session.
- **Returns**: a verdict line, then one line per plan row, then out-of-scope findings, then the quoted tail of the test output. The per-row list is the one place the terse-returns cap does not apply, since it scales with the plan.
- It must **run** the command. A verdict reasoned from the diff alone gets rejected and re-run.

## Parent-side guards

A boundary written in a prompt is a request. These checks are what make it a control. Run the guard for the role immediately after the agent returns.

| After | Guard |
|---|---|
| Any agent | Read the diff yourself. Never accept the summary as evidence. |
| `supercook-implementer` | Test integrity and scope, both below. Run before committing. |
| `supercook-verifier` | Confirm fresh test output is quoted. No output means re-run. |
| `supercook-plan-judge` | Confirm every slice has an estimate inside budget or a logged exception. |
| `supercook-test-designer` | Confirm the new tests actually fail, and fail for the intended reason. |

### Test integrity and scope guards

Both mechanisms are defined once, in [pipeline/implementation.md](pipeline/implementation.md#the-guards), because that is the phase where they run. Do not keep a second copy here: two copies of the load-bearing safety rule is exactly what the DRY principle in `SKILL.md` argues against, and the copy that drifts is the one that gets followed.

The one-line summary, so this table is readable without a second file open: detect with `git status --porcelain --untracked-files=all` before committing, restore modified tests, delete added ones, log every intervention, and route a genuinely wrong test to `supercook-test-designer` as an amendment rather than editing it here.

## Fallback when the agents are not installed

The skill still works without the plugin's agents, for instance when someone copies the skill folder alone or discovery is off. Detect it during the intake probe, then for each role:

1. Read `agents/supercook-<role>.md` and use its body as the prompt.
2. Launch `generalPurpose`, or `explore` for recon work.
3. Keep the same inputs, done-when, returns shape, and guards.
4. Log one ledger row noting the degraded path.

The assessor is small enough that the parent can simply classify inline instead of launching anything.
