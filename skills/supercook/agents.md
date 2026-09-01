# Agent launch contracts

The nine agents live at the plugin root in `agents/`, not in this skill folder. That is where Cursor discovers them, so they show up as real delegatable subagents. Every name is prefixed `supercook-` so a public install cannot collide with someone's own `implementer` or `verifier`.

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
| `supercook-plan-optimizer` | plan-optimizer | `plan.md` only | 4 |
| `supercook-test-designer` | standard | Test files only | 5 |
| `supercook-implementer` | implementer | Source, never tests | 6 |
| `supercook-verifier` | standard | No source edits, runs commands | 7 |

## What every launch includes

Pass these on every launch, without exception:

- **The objective**, in one sentence, specific to this run.
- **The run folder path**, so the agent can read `plan.md`, `user-plan.md`, and `design-doc.md` when relevant. Never ask an agent to write the ledger.
- **Its inputs**: file pointers from recon, the scope list, the test command, whatever that role needs.
- **Its UI inputs, when relevant**: only the resolved brief, evidence, contract
  entries, and owned obligations that role needs. The parent retrieves designs and
  owns rendered smoke.
- **The model**, taken from the roster intake resolved (see [models.md](models.md)), or nothing when the role is `inherit`. Resolve once at intake, not per launch.
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
  track: bugfix | feature | investigation | refactor | open-pr | merge | implement-plan
  big-change: yes | no
  why: <one sentence naming what drove the verdict>
  ```
- **`merge` is user-selected, never inferred.** Return it only when the user asked for an existing PR to be merged. A task that will produce a PR is not a merge request.
- **`implement-plan` is user-selected, never inferred.** Return it only when the user asked to implement a plan they already wrote. The parent normally routes this track before the assessor runs at all.

### supercook-explorer

- **Inputs**: a scoped question list. One area per launch. Launch several in parallel for a broad task.
- **Effort budget**: about 10 tool calls per launch.
- **Done when**: every question in its scope has a `file:line` pointer or an explicit "not found".
- **Returns**: pointers first, then a how-it-works note capped at 10 lines. No file dumps, no pasted implementations.
- **Also returns on the broad launch**: the repo's test path patterns and the exact command that runs the suite. Later phases depend on both.
- **Also returns for UI work**: `ui-change` plus the evidenced start command,
  readiness signal, route, seed or auth state, viewport mechanism, and teardown.
  Unknown facts say `not found`.

### supercook-planner

- **Inputs**: task, tier, track, recon pointers, the Design Doc when one exists, the resolved UI brief and evidence when one exists, the slice budget.
- **Effort budget**: one pass. Plan, do not explore. If it needs to explore, recon was too thin.
- **Done when**: `plan.md` exists with numbered slices, each carrying scope, a named verification, and a reviewable-line estimate. Contract-level UI also has complete source-of-truth entries, owned obligations on each UI slice, and exactly one reachable order-test owner per contract.
- **Returns**: the slice list, one line each, and the total estimate.

### supercook-arena-runner

- **Inputs**: identical brief for all three, plus recon pointers and the same resolved UI brief and evidence when one exists. The only difference between launches is the model.
- **Effort budget**: one pass, no implementation, no file writes outside its own candidate plan.
- **Done when**: a complete candidate plan exists in its own file, with slices, risks, and the one decision it is least sure about. Contract-level UI also has complete source-of-truth entries, slice ownership, and one reachable order-test owner per contract.
- **Returns**: the approach in two sentences, the slice list with estimates, and its least-sure decision. Not the plan itself: the judge reads the candidate files directly, so returning the full plan would put three plans in the parent's context for no reason.

### supercook-plan-judge

- **Inputs**: all three candidate plans, the recon pointers, the resolved UI brief and evidence when one exists, the slice budget.
- **Effort budget**: read, compare, decide, write. No new exploration.
- **Done when**: `plan.md` is written, every slice is inside the budget or carries a logged cohesion exception, and any required UI contract is complete with explicit slice ownership and one reachable order-test owner.
- **Judging criteria**, in order: correctness against code and supplied design, slice sizing and independence, surgical scope, risk named honestly.
- **Returns**: which plans contributed to which slices, and the strongest idea it rejected plus why.

### supercook-plan-optimizer

- **Inputs**: `user-plan.md` in the run folder, recon pointers, the resolved UI brief and evidence when one exists, the slice budget.
- **Effort budget**: one pass. Read the supplied plan and the recon pointers. Do not explore.
- **Boundaries**: honor the user's approach and decisions. Write only `plan.md`. Never invent a different approach; a materially better idea goes in `dissent`, not the plan.
- **Done when**: `plan.md` exists with numbered slices, each carrying scope, a named verification, and a reviewable-line estimate, plus `## Changes from your plan`. Contract-level UI also has complete source-of-truth entries, owned obligations on each UI slice, and exactly one reachable order-test owner per contract.
- **Returns**: the slice list with estimates, the total, the changes list (or `no changes beyond slicing`), and `dissent`.

### supercook-test-designer

- **Inputs**: the slice, the journeys it serves, the test command, the repo's test conventions from recon, referenced UI contract entries plus owned obligations, `mode: red-first | retrospective-open-pr`, and `verification: tests | recipe`.
- **Effort budget**: as long as the journeys need, but no implementation.
- **Done when**: the named journeys have tests or an executable recipe and the selected verification runs. Red-first verification fails for the intended missing behavior; retrospective-open-pr verification reports an honest pass or gap. Contract-level UI pins each slice's owned anchors, counts, grouping, and interactions; only the named owner pins the global order.
- **Returns**: verification kind, test paths or recipe, one line per journey, the exact command and result, the run-folder destination the parent records for a recipe, and UI contract coverage when present.
- **Owns every test edit for the whole run.** A test that needs changing comes back here, never to the implementer.
- **Open-pr retrospective mode**: contract tests are allowed to pass against source
  that already existed. Label the evidence retrospective rather than claiming a
  red-first failure.

### supercook-implementer

- **Inputs**: the slice scope as an explicit file list, the data shape, the failing tests or recorded recipe, the exact verification command, and for contract-level UI the entry, source locator, resolved brief, retained visual evidence, and owned obligations.
- **Effort budget**: as long as it takes to green the named tests, and not one file further.
- **Boundaries**: never edit, add, or delete a test file or verification recipe. Never touch a path outside the scope list. Something outside scope that looks wrong gets reported, not fixed.
- **Done when**: the recorded verification passes and no file outside the scope list is modified. Contract-level UI also requires the evidence to be consumed before a view edit and all owned obligations to match it.
- **Returns**: changed paths, the command it ran with its result, `design-evidence` for contract-level UI, and anything it wanted to change but did not.

### supercook-verifier

- **Inputs**: `plan.md`, the ledger, the diff, and the test command or recorded executable recipe plus its expected checksum. Open-pr supplies its initial diff inventory and can supply its retrospective ledger contract instead of `plan.md`. Fresh context only, no implementation history.
- **Effort budget**: enough to run the recorded verification and check every contract row.
- **Done when**: every plan row, or every retrospective ledger row on open-pr, is marked landed or missing with evidence, the tests or recipe have run in this session, and any UI contract obligations are checked in source and verification.
- **Returns**: a verdict line, one line per contract row, out-of-scope findings, `ui-contract: ok | mismatch | not applicable`, recipe checksum status when relevant, then the quoted verification output. It never returns `visual: ok`; the parent renders.
- It must **run** the command. A verdict reasoned from the diff alone gets rejected and re-run.

## Parent-side guards

A boundary written in a prompt is a request. These checks are what make it a control. Run the guard for the role immediately after the agent returns.

| After | Guard |
|---|---|
| Any agent | Read the diff yourself. Never accept the summary as evidence. |
| `supercook-explorer` | For UI work, confirm every render field has evidence or says `not found`. |
| `supercook-planner` / `supercook-plan-judge` | Confirm every slice has an estimate inside budget or a logged exception. For contract UI, run the plan-completeness guard in `pipeline/ui.md`. |
| `supercook-plan-optimizer` | Same slice-budget and UI plan-completeness check as planner and judge. Also confirm `## Changes from your plan` exists, and that every change line references something real: a recon pointer or the user's plan text. `no changes beyond slicing` is a valid section body. |
| `supercook-test-designer` | Confirm the selected tests or recipe fail for the intended reason, except labeled open-pr retrospective verification. Run the anchor and order guard in `pipeline/implementation.md`. |
| `supercook-implementer` | Run recipe-checksum, test-integrity, and scope guards. Contract UI also requires a valid `design-evidence` return. Run before committing. |
| `supercook-verifier` | Confirm fresh test or recipe output is quoted and any recipe checksum matched. Contract UI requires `ui-contract: ok`, and any visual claim is rejected. |

### Implementation guards

Recipe integrity, test integrity, and scope are defined once in
[pipeline/implementation.md](pipeline/implementation.md#the-guards), because that
is where they run. Do not keep a second copy here: duplicated safety rules drift.

The one-line summary: compare a recorded recipe checksum, detect source and test
changes with `git status --porcelain --untracked-files=all`, restore modified tests,
delete added tests, log every intervention, and route a genuinely wrong test or
recipe to `supercook-test-designer`.

UI controls live in two places rather than being copied here:

- [pipeline/ui.md](pipeline/ui.md) defines classification, contract completeness,
  evidence, deviations, structural verification, and parent-owned rendered smoke.
- [pipeline/implementation.md](pipeline/implementation.md#ui-contract-guard)
  defines the executable anchor and order-test guard.

## Fallback when the agents are not installed

The skill still works without the plugin's agents, for instance when someone copies the skill folder alone or discovery is off. Detect it during the intake probe, then for each role:

1. Read `agents/supercook-<role>.md` and use its body as the prompt.
2. Launch `generalPurpose`, or `explore` for recon work.
3. Keep the same inputs, done-when, returns shape, and guards.
4. Log one ledger row noting the degraded path.

The assessor is small enough that the parent can simply classify inline instead of launching anything.
