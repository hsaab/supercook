# Agent launch contracts

The nine agents live at the plugin root in `agents/`, not in this skill folder. Each is a Cursor custom subagent file (YAML frontmatter with `name`, `description`, `model`, `readonly`), so Cursor discovers it from the installed plugin's `agents/` directory, or from `~/.cursor/agents/` on a host that mirrors only the skill (see the README install notes), and it shows up as a named subagent the parent can launch with `/supercook-<role>` or "use the supercook-<role> subagent". Consumer repositories never need a copy in their own `.cursor/agents/`. Every name is prefixed `supercook-` so a public install cannot collide with someone's own `implementer` or `verifier`.

**Finding an agent file.** `agents/supercook-<role>.md` is a path from the plugin root, two folders up from this skill folder (`../../agents/` from here), and is a different thing from this `agents.md` file. When this skill folder was mirrored on its own and has no plugin root above it, read the file from `~/.cursor/agents/`, then from `~/.cursor/plugins/local/supercook/agents/`.

This file is the launch contract: what the parent passes in, when the job is done, what comes back, and what the parent checks afterwards. The prompt itself lives in the agent file.

## Contents

- [Launch mechanism](#launch-mechanism)
- [The roster](#the-roster)
- [What every launch includes](#what-every-launch-includes)
- [Per-role contracts](#per-role-contracts)
- [Parent-side guards](#parent-side-guards)
- [Spawn paths when typed agents are missing](#spawn-paths-when-typed-agents-are-missing)

## Launch mechanism

Pick the spawn path from the tools this session actually lists, per [Spawn paths](#spawn-paths-when-typed-agents-are-missing). Whatever the tool, pass an explicit **`model`** argument when the tool accepts one. Take the slug from the intake **`models-resolved:`** ledger line (or the same map you just validated at intake) for that agent's roster key in [models.md](models.md). **Omit `model` only when that role resolved to `inherit`.** The `model: inherit` frontmatter in an agent file does not select a model; the parent must pass it on the launch call or the session default runs and the roster hook may deny the launch.

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

- **`supercook-role:` and `supercook-run:` tags**, line-anchored in the prompt body. Use the roster key from the table above (`standard` for assessor, planner, test-designer, and verifier; `explorer`, `implementer`, `arena-a`, `arena-b`, and `arena-c` as separate keys; a review-track implementer launch uses `review-implementer`, not `implementer`). The run tag is this run's folder path (absolute, or relative to the workspace). Host reviewers on the review track follow [playbooks/review.md](playbooks/review.md) for placement inside fixed prompt shapes.
- **The objective**, in one sentence, specific to this run.
- **The run folder path**, so the agent can read `plan.md`, `user-plan.md`, and `design-doc.md` when relevant. Never ask an agent to write the ledger.
- **Its inputs**: file pointers from recon, the scope list, the test command, whatever that role needs.
- **Its UI inputs, when relevant**: only the resolved brief, evidence, contract
  entries, and owned obligations that role needs. The parent retrieves designs and
  owns rendered smoke.
- **The model**, taken from the ledger `models-resolved:` map (see [models.md](models.md) and [pipeline/intake.md](pipeline/intake.md)), passed on every launch whose spawn tool accepts a model field, or omitted only when that role is `inherit`. Resolve once at intake, then reuse the ledger line on resume; do not re-guess per launch.
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

- **Inputs**: the slice scope as an explicit file list, the data shape, the failing tests or recorded recipe, the exact verification command, and for contract-level UI the entry, source locator, resolved brief, retained visual evidence, and owned obligations.
- **Effort budget**: as long as it takes to green the named tests, and not one file further.
- **Boundaries**: never edit, add, or delete a test file or verification recipe. Never touch a path outside the scope list. Something outside scope that looks wrong gets reported, not fixed.
- **Done when**: the recorded verification passes and no file outside the scope list is modified. Contract-level UI also requires the evidence to be consumed before a view edit and all owned obligations to match it.
- **Returns**: changed paths, the command it ran with its result, `design-evidence` for contract-level UI, and anything it wanted to change but did not.
- **Review-track variant**: one launch per slice PR, on the `review-implementer` model instead of `implementer`. Inputs swap the failing tests for the triaged findings list (file, claim, surviving evidence per finding); the scope list is the union of files the findings name, and the PR's recorded test command is the verification. Boundaries, done-when, returns, and the parent-side guard are unchanged. See [playbooks/review.md](playbooks/review.md).

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
| Any launch | Model enforcement already ran in the preToolUse roster hook (see [models.md](models.md)). After the agent returns, log the model slug actually passed on every launch row in the ledger (or `inherit` when omitted). |
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

Every roster role is a **named subagent launch**: launch the subagent `supercook-<role>` (in Cursor terms, invoke `/supercook-<role>` or say "use the supercook-<role> subagent"), with the role and run tags, the body of `agents/supercook-<role>.md`, and this launch's brief as its prompt. This skill never requires a particular spawn tool by name. Use whatever spawn tool **this session actually lists**; hosts differ, and the same host can differ between sessions.

Typed `supercook-*` subagents are sometimes missing from the host catalog, for instance on a Cloud Agent VM, a Project worker, or a skill-only copy. Agent files on disk do not by themselves make them typed agents: only the catalog does, and the catalog is fixed when the session starts. Intake records which path applies as `spawn:` on the capability line ([pipeline/intake.md](pipeline/intake.md#1-probe-capabilities)). Use the first path that applies, role by role: a session that loaded an older install can list eight typed agents and no `supercook-plan-optimizer`, and then only that role drops to the second path.

A spawn tool is not always in the top-level tool list. Check the tool list, any deferred or dynamic tool catalog (open its namespaces and read what they hold), and the subagent types before recording `none`. A real `none` does exist: a parent that was itself launched as a subagent often has no spawn tool (Cursor allows at most one more level below a direct subagent, and some sessions list none even there), and hooks or tool policy can remove it as well. Never call a tool, namespace, or envelope you cannot see, and never wait for, guess, or invent a spawn tool that is not listed: a coordinator's `CallDynamicTool` / `Task` shape in [.cursor/supercook/subagent-launch.md](../../.cursor/supercook/subagent-launch.md) applies only when that tool is in the catalog.

| `spawn:` | When | How each roster role runs |
|---|---|---|
| `typed` | `supercook-*` agents are in the catalog (plugin installed, or files in `~/.cursor/agents/`) | Launch the named `supercook-<role>` subagent, per the contracts above. |
| `<tool name>` | No typed agents, but some nested-spawn tool is listed | Launch a worker named `supercook-<role>` through that tool with the agent file body as the prompt. See [the host recipes](#host-recipes). |
| `none` | No nested-spawn tool of any kind | The parent runs each role itself from its agent file. See [No spawn tool](#no-spawn-tool-run-roles-inline). |

### Host recipes

The tool names below are examples of what a session might list, not a required API. Map the same intent onto whichever tool you see.

- **Name the worker.** If the spawn tool has a field for the subagent's type or name, set it to `supercook-<role>` when the host accepts that name; otherwise use the host's general-purpose type (or its read-only explore type for recon) and put `supercook-<role>` in the description. Either way the prompt carries the role and run tags, then the body of `agents/supercook-<role>.md`, then the brief.
- **Pass `model`** from the ledger `models-resolved:` map when the tool has a model field; omit it only for `inherit`.
- **Field placement for `Task` and `CreateAgent`.** When the session lists `CallDynamicTool` with a `cursor` `Task` tool, or a top-level `CreateAgent` / `Subagent`, the envelope rules and pre-flight validator are in [.cursor/supercook/subagent-launch.md](../../.cursor/supercook/subagent-launch.md). Any other spawn tool follows its own listed schema.

**Keep workers on the parent's machine.** When the spawn tool offers a choice (`environment: local` or similar), use the local, same-checkout option so the worker can read the run folder under `.supercook/`. A Cloud Agent parent never asks for a nested cloud VM on purpose. When the tool only offers a separate VM, or the worker reports it cannot see the run folder, that worker gets no `.supercook/` access: push the run branch before launch, put the slice scope, `plan.md` content, and every input inline in the prompt, and have a writing role (test-designer, implementer) commit and push its work to the run branch. The parent then fetches, reads that diff itself, and runs the role's guard before continuing.

### Phase map (same contract, any path)

| Phase | Agent file | Note |
|---|---|---|
| 1 assess | `agents/supercook-assessor.md` | Launched when a spawn tool exists; inline only with `spawn: none`. |
| 2 recon | `agents/supercook-explorer.md` | One launch per area, in parallel when the tool allows it. |
| 4 plan | `agents/supercook-planner.md` (or arena, judge, optimizer) | Arena runners go out in one batch. |
| 5 test-first | `agents/supercook-test-designer.md` | Tests committed before phase 6. |
| 6 implement | `agents/supercook-implementer.md` | With a spawn tool, **never** the parent on standard or complex tier. |
| 7 verify | `agents/supercook-verifier.md` | With a spawn tool, a fresh worker, **never** the parent on standard or complex tier. |

For each launch:

1. Read `agents/supercook-<role>.md` and use its body as the prompt, after the line-anchored `supercook-role:` and `supercook-run:` tags.
2. Pass `model` from the ledger `models-resolved:` map when the tool accepts it; omit only for `inherit`.
3. Keep the same inputs, done-when, returns shape, and parent-side guards from this file.
4. Log one ledger row with the spawn tool name, the worker name, and the model slug (or `inherit`).

### No spawn tool: run roles inline

When `spawn: none`, every roster role runs in the parent from its agent file body. This is the original Supercook fallback, and it is the honest one: do not invent launch ceremony or rows for launches that never happened.

1. At the start of each roster phase, read `agents/supercook-<role>.md` and do that role's job under its contract: the same inputs, effort budget, boundaries, done-when, and returns shape.
2. Write the role's return into the ledger as if a worker had returned it, on a row marked `degraded: parent inline (spawn none)`. Tags and model fields do not apply.
3. Run the parent-side guard for that role exactly as after a launch. The pipeline still runs in full on standard and complex tier: recon pointers, `plan.md`, red tests committed before source, implementation inside the scope list, and a verifier pass.
4. Run the verifier role with a fresh read: re-open `plan.md`, the ledger, and `git diff` from disk instead of relying on what you remember writing, then run the test command and quote its output.

### Forbidden skips

On standard or complex tier, these ledger reasons are **invalid** unless assessor approved **trivial** tier collapse:

- `skip: agents not installed`
- `skip: user checklist`
- `skip: coordinator spec`
- `skip: plan included in kickoff`
- `skip: faster inline`
- `skip: small task`

Missing agents change who runs a role, never whether it runs. A Project or cloud assignment that pastes the implementation is still intake plus assessor first. Checklist text does not waive explorer, planner, implementer, test-designer, or verifier, whichever path runs them. Neither does a parent's own sense that the work is small or that one pass would be quicker: size is the assessor's verdict to give. Having a spawn tool and implementing alone anyway is the failure this section exists to stop.
