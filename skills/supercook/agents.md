# Agent launch contracts

The nine agents live at the plugin root in `agents/`, not in this skill folder. Each is a Cursor custom subagent file (YAML frontmatter with `name`, `description`, `model`, `readonly`), so Cursor discovers it from the installed plugin's `agents/` directory, or from `~/.cursor/agents/` on a host that mirrors only the skill (see the README install notes), and it shows up as a named subagent the parent can launch with `/supercook-<role>` or "use the supercook-<role> subagent". A listed type is launched as that type, and its prompt body can lag the skill. A role that is not listed is launched by the spawn shape rule in [SKILL.md](SKILL.md#start-here-the-launch-rule), with the agent file body as the prompt. Copying agent files is the installer's job, not a step the parent takes during a run. Every name is prefixed `supercook-` so a public install cannot collide with someone's own `implementer` or `verifier`.

This file is the launch contract: what the parent passes in, when the job is done, what comes back, and what the parent checks afterwards. The prompt itself lives in the agent file.

Whether to launch is already decided by [Start here](SKILL.md#start-here-the-launch-rule): every roster phase that runs is a launch, at every tier, unless the session has no spawn tool. This file only says how.

**Finding an agent file.** `agents/supercook-<role>.md` is a path from the plugin root, two folders up from this skill folder (`../../agents/` from here), and is a different thing from this `agents.md` file. When this skill folder was mirrored on its own, read the file from `~/.cursor/agents/`, then from `~/.cursor/plugins/local/supercook/agents/`. If none of those has it, launch the worker anyway with that role's block under [Per-role contracts](#per-role-contracts) as the prompt body, and log `agent file missing` on the launch row. A missing prompt file never moves a role to the parent.

## Contents

- [Launch mechanism](#launch-mechanism)
- [The roster](#the-roster)
- [What every launch includes](#what-every-launch-includes)
- [Per-role contracts](#per-role-contracts)
- [Parent-side guards](#parent-side-guards)
- [Spawn paths when typed agents are missing](#spawn-paths-when-typed-agents-are-missing)

## Launch mechanism

Pick the spawn path from the tools this session actually lists, per [Spawn paths](#spawn-paths-when-typed-agents-are-missing). Pass the **`model`** argument when the tool accepts one, taking the slug from the ledger `models:` line for that agent's roster key in [models.md](models.md). Omit `model` for a role that is `inherit`. The `model: inherit` frontmatter in an agent file does not select a model; the parent passes it on the launch call. Models are a preference: if a launch rejects the model, the retry ladder in [SKILL.md](SKILL.md#start-here-the-launch-rule) drops the field and relaunches.

**Arena (complex tier):** launch three `supercook-arena-runner` subagents in parallel in one message. Pass `arena-a`, `arena-b`, and `arena-c` models respectively (omit `model` only for a role that resolved to `inherit`).

## The roster

| Agent | Role in models.md | Writes files? | Phase |
|---|---|---|---|
| `supercook-assessor` | standard | No | 1 (skipped on `merge`, `implement-plan`, and `review` tracks) |
| `supercook-explorer` | explorer | No | 2 |
| `supercook-planner` | standard | `plan.md` only | 4 |
| `supercook-arena-runner` | arena-a, arena-b, arena-c | Its own candidate plan only | 4 |
| `supercook-plan-judge` | plan-judge | `plan.md` only | 4 |
| `supercook-plan-optimizer` | plan-optimizer | `plan.md` only | 4 |
| `supercook-test-designer` | standard | Test files only | 5 |
| `supercook-implementer` | implementer (`review-implementer` when launched from the review playbook) | Source, never tests | 6 |
| `supercook-verifier` | standard | No source edits, runs commands | 7 |

The review track also launches up to four host reviewer subagents (`bugbot`, `security-review`, and the two thermo reviewers) that are not supercook agents; `bugbot` and `security-review` are skipped when a usable hosted run of theirs exists on the PR head, per the source table in the playbook. Their model is the `reviewer` role in [models.md](models.md); everything else about them is fixed by their own contracts. See [playbooks/review.md](playbooks/review.md).

## What every launch includes

Pass these on every launch, without exception:

- **The roster key**, so the launch row and a resumed session can tell which `models:` entry applied: take it from the **Role in models.md** column in [The roster](#the-roster) and the fenced block in [models.md](models.md#the-roster) (`plan-judge` and `plan-optimizer` are their own keys, not `standard`). Say it in the prompt as plain text (`roster key: explorer`).
- **The objective**, in one sentence, specific to this run.
- **The run folder path**, so the agent can read `plan.md`, `user-plan.md`, and `design-doc.md` when relevant. Never ask an agent to write the ledger.
- **Its inputs**: file pointers from recon, the scope list, the test command, whatever that role needs.
- **Its UI inputs, when relevant**: only the resolved brief, evidence, contract
  entries, and owned obligations that role needs. The parent retrieves designs and
  owns rendered smoke.
- **The model**, per [Launch mechanism](#launch-mechanism): the `models:` ledger entry for this role, unless the user changed it mid-run.
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
- **`merge` is user-selected, never inferred.** Return it only when the user asked for an existing PR to be merged, with **no** `review` in the primary ask. A task that will produce a PR is not a merge request.
- **`review` is user-selected, never inferred.** The parent routes `review` and `review and merge` before the assessor runs. **`review and merge` is review track for classification**, not `merge`. Never return `merge` when the primary ask includes `review`.
- **`implement-plan` is user-selected, never inferred.** Return it only when the user asked to implement a plan they already wrote. The parent normally routes this track before the assessor runs at all.
- **Do not launch the assessor on the review track.** Stack resolution and bottom-up review are intake plus [playbooks/review.md](playbooks/review.md), not an assessor pass.

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

- **Inputs**: the slice scope as an explicit file list, the data shape, the failing tests or recorded recipe, the exact verification command, and for contract-level UI the entry, source locator, resolved brief, retained visual evidence, and owned obligations. A trivial run has no plan and no red test: the inputs are the task text, the file scope, and the recorded test command, and done-when is the change made with that command passing.
- **Effort budget**: as long as it takes to green the named tests, and not one file further.
- **Boundaries**: never edit, add, or delete a test file or verification recipe. Never touch a path outside the scope list. Something outside scope that looks wrong gets reported, not fixed.
- **Done when**: the recorded verification passes and no file outside the scope list is modified. Contract-level UI also requires the evidence to be consumed before a view edit and all owned obligations to match it.
- **Returns**: changed paths, the command it ran with its result, `design-evidence` for contract-level UI, and anything it wanted to change but did not.
- **Review-track variant**: one launch per slice PR, on the `review-implementer` model instead of `implementer`. Inputs swap the failing tests for the triaged findings list (file, claim, surviving evidence per finding); the scope list is the union of files the findings name, and the PR's recorded test command is the verification. Boundaries, done-when, returns, and the parent-side guard are unchanged. See [playbooks/review.md](playbooks/review.md).

### supercook-verifier

- **Inputs**: `plan.md`, the ledger, the diff, and the test command or recorded executable recipe plus its expected checksum. Open-pr supplies its initial diff inventory and can supply its retrospective ledger contract instead of `plan.md`. A trivial run has no `plan.md`: the task text and the ledger's `done:` predicate are the contract instead. Fresh context only, no implementation history.
- **Effort budget**: enough to run the recorded verification and check every contract row.
- **Done when**: every plan row, or every retrospective ledger row on open-pr, is marked landed or missing with evidence, the tests or recipe have run in this session, and any UI contract obligations are checked in source and verification.
- **Returns**: a verdict line, one line per contract row, out-of-scope findings, `ui-contract: ok | mismatch | not applicable`, recipe checksum status when relevant, then the quoted verification output. It never returns `visual: ok`; the parent renders.
- It must **run** the command. A verdict reasoned from the diff alone gets rejected and re-run.

## Parent-side guards

A boundary written in a prompt is a request. These checks are what make it a control. Run the guard for the role immediately after the agent returns.

| After | Guard |
|---|---|
| Any roster phase | Before checking its ledger row, confirm the launch record that [ledger rule 6](pipeline/ledger.md#rules) requires. Without one, reopen the row and launch the worker. |
| Any launch | After the agent returns, log the model actually used on the launch row (`inherit` when the field was omitted or dropped). No hook checks it against the roster. |
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

## Spawn paths when typed agents are missing

Every roster role is a **named subagent launch**: launch the subagent `supercook-<role>` (in Cursor terms, invoke `/supercook-<role>` or say "use the supercook-<role> subagent"), with the roster key and run folder path from [What every launch includes](#what-every-launch-includes), the body of `agents/supercook-<role>.md`, and this launch's brief as its prompt. This skill never requires a particular spawn tool by name. Use whatever spawn tool **this session actually lists**; hosts differ, and the same host can differ between sessions.

Typed `supercook-*` subagents are sometimes missing from the host catalog, for instance on a Cloud Agent VM, a Project worker, or a skill-only copy. Agent files on disk do not by themselves make them typed agents: only the catalog does, and the catalog is fixed when the session starts. Intake records which path applies as `spawn:` on the capability line ([pipeline/intake.md](pipeline/intake.md#1-probe-capabilities)). Use the first path that applies, role by role: a session that loaded an older install can list eight typed agents and no `supercook-plan-optimizer`, and then only that role drops to the second path.

A spawn tool is not always in the top-level tool list. Check the tool list, any deferred or dynamic tool catalog (open its namespaces and read what they hold), and the subagent types before recording `none`. A real `none` does exist: a parent that was itself launched as a subagent often has no spawn tool, and tool policy can remove it. Never call a tool, namespace, or envelope you cannot see. The spawn shape rule and retry ladder are in [SKILL.md](SKILL.md#start-here-the-launch-rule).

| `spawn:` | When | How each roster role runs |
|---|---|---|
| `typed` | `supercook-*` agents are in the catalog (plugin installed, `.cursor/agents/` from the repo installer, or files in `~/.cursor/agents/`) | Launch the named `supercook-<role>` subagent, per the contracts above. |
| `<tool name>` | No typed agents, but some nested-spawn tool is listed | Launch a worker named `supercook-<role>` through that tool with the agent file body as the prompt, using the spawn shape rule in [SKILL.md](SKILL.md#start-here-the-launch-rule). See [the host recipes](#host-recipes). |
| `none` | No nested-spawn tool of any kind | The parent runs each role itself from its agent file. See [No spawn tool](#no-spawn-tool-run-roles-inline). |

### Host recipes

The tool names below are examples of what a session might list, not a required API. Map the same intent onto whichever tool you see.

- **Name the worker.** Read the spawn tool's own schema, per [SKILL.md](SKILL.md#start-here-the-launch-rule). When `supercook-<role>` is a listed type, launch it as that listed type. When the type field accepts a free value and the tool has a separate name field, set the type to `custom` and the name to `supercook-<role>`. Otherwise use the host's general-purpose type and put `supercook-<role>` in the description, with the agent file body as the prompt. Either way the prompt carries the roster key and run folder path from [What every launch includes](#what-every-launch-includes), then the body of `agents/supercook-<role>.md`, then the brief.
- **Field placement for `Task` and `CreateAgent`.** Through `CallDynamicTool` (`namespace: cursor`, `toolName: Task`), every launch field (`description`, `subagent_type`, `prompt`, optional `model`) goes under `arguments`, and `prompt` is a plain string, not a file path. A top-level `CreateAgent` or `Subagent` takes the same fields at the top level. If a launch fails with `prompt ... undefined`, build it with `python3 scripts/validate_subagent_launch.py task --prompt-file <file>` and paste the printed JSON. Any other spawn tool follows its own listed schema.

**Keep workers on the parent's machine.** When the spawn tool offers a choice (`environment: local` or similar), use the local, same-checkout option so the worker can read the run folder under `.supercook/`. A Cloud Agent parent never asks for a nested cloud VM on purpose. When the tool only offers a separate VM, or the worker reports it cannot see the run folder, that worker gets no `.supercook/` access: push the run branch before launch, put the slice scope, `plan.md` content, and every input inline in the prompt, and have a writing role (test-designer, implementer) commit and push its work to the run branch. The parent then fetches, reads that diff itself, and runs the role's guard before continuing.

### The same contract on any path

The worker for each phase is the "Run by" column of [the pipeline table](SKILL.md#the-pipeline), and its prompt body is `agents/<worker name>.md`. Whichever path launches it, keep the same inputs, done-when, returns shape, and parent-side guards from this file, and log one ledger row with the spawn tool name, the worker name, and the model slug (or `inherit`).

### No spawn tool: run roles inline

This is solo mode. It applies when `spawn: none`, and for the rest of a run once the retry ladder ends in solo mode. The phases, tier collapse, and ledger rows are the same as a normal run. What changes is who does the work, so the guarantees come from files and git instead of a second agent. Mark each row `inline`. At each phase, work from that role's contract in this file, and open `agents/supercook-<role>.md` only when the contract is not enough.

Every phase hands off through a file in the run folder, never through chat memory:

- **Assess.** Run inline and write the 4-line verdict on the row. It stays first because the tier decides how much of the rest runs.
- **Recon** (standard and complex). One area at a time, about 10 tool calls per area. Write `recon.md` with pointers and the test command, no file dumps.
- **Design doc.** Unchanged: the parent always ran it with the user.
- **Plan.** Write `plan.md` in the planner format: numbered slices, a scope file list, a named verification, and a line estimate. Then review it once against the judge criteria in [pipeline/planning.md](pipeline/planning.md): correct against the code, slice size and independence, surgical scope, risk named honestly. Add `## Strongest objection` with what changed because of it. On complex tier the arena does not run: log `arena: n/a (solo)`. On `implement-plan`, tighten `user-plan.md` and add `## Changes from your plan`, like the optimizer.
- **Test-first.** Unchanged. Run the tests, confirm they fail for the intended reason, commit them alone, and record that SHA on the row.
- **Implement.** One slice at a time, inside that slice's scope list. Before each commit, `git diff --name-only <tests-sha>..HEAD -- <test paths>` must print nothing, and `git status --porcelain --untracked-files=all` must show only scope files.
- **Verify.** Run it after the slice is committed, so it audits the artifact and not your memory. Re-open `plan.md` and `git diff <base>...HEAD` from disk, run the test command, and write one line per plan row (landed, missing, or partial) plus the quoted output to `verify.md`. The gap loop and escape rule in [pipeline/verification.md](pipeline/verification.md) are unchanged.
- **Deliver.** The PR body says "built in solo mode: verify was a self-audit". A hosted Bugbot run on the PR is the independent review. On the review track only hosted reviewers run, since local reviewers need a spawn tool.

Want a human check on the plan? `/supercook plan only <task>`, read `plan.md`, then `/supercook use this plan`. That flow works in solo mode too.

Write each return into the ledger as if a worker had returned it. Do not invent launch rows for launches that never happened.

### Forbidden skips

A skip removes a phase. It never moves a phase from its worker to the parent while a spawn tool works. The invalid ledger reasons are listed once, in [pipeline/ledger.md](pipeline/ledger.md#invalid-skip-reasons). Solo mode is the only case where the parent runs a roster role.
