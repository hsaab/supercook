# Kickoff messages and parent invariants

Supercook runs on more than one host. The parent may be a Cursor chat agent, a Project worker, a Cloud Agent checkout, or another entry that loaded the skill. Spawn tools differ from host to host and session to session (typed `supercook-*` agents in the catalog, `Task`, `CreateAgent`, host `Subagent`, some other nested-spawn tool, or nothing at all). The rules below do not: every roster role is a launch of the named subagent `supercook-<role>` through whatever this session lists.

## Non-negotiables (every host)

These apply whether the user invoked `/supercook` in chat or a coordinator pasted a worker brief.

1. **Turn 1:** Read [../SKILL.md](../SKILL.md) in full before intake edits, assessor skip logic, or any repo change.
2. **Intake then assessor:** Phase 0 and phase 1 complete (or a user-selected track that legitimately skips assessor per [../SKILL.md](../SKILL.md)) before implementation, workflow, or delivery edits.
3. **Checklist is not a plan:** A pasted file list, YAML block, pytest recipe, or step-by-step implement list is a *spec pointer* at most. It does not replace recon, planner output in `plan.md`, test-first rows, verifier, or ledger phases.
4. **Launch the named subagent with the spawn tool you actually have:** Launch `supercook-<role>` (`/supercook-<role>` or "use the supercook-<role> subagent") when typed agents are in the catalog. When they are missing, each roster role runs through the first path that exists in this session ([../agents.md](../agents.md#spawn-paths-when-typed-agents-are-missing)): any listed spawn tool, launching a worker named `supercook-<role>` with `agents/supercook-<role>.md` as the prompt body, or, only when no spawn tool exists, the parent running that role inline from its agent file. A parent that has a spawn path does not do roster work itself at any tier: a **trivial** verdict from the assessor removes recon, plan, and test-first, and the implement and verify phases that remain are still an implementer launch and a verifier launch ([../SKILL.md](../SKILL.md#start-here-the-launch-rule)). Never call a tool that is not in your catalog.
5. **Invalid ledger skip:** `skip: user checklist`, `skip: coordinator spec`, or `skip: agents not installed` without assessor-approved trivial collapse is never valid on standard/complex work. Missing agents change who runs a role, never whether it runs.

## Good kickoff vs bad kickoff

| Good | Bad |
|------|-----|
| States the **objective** in one sentence | Pastes the entire implementation as the only message |
| States **done-when** as a testable predicate | Lists commands to run with no pipeline phases |
| Points at a **spec path** (`docs/foo.md`, issue link) for detail | Embeds Package C YAML/pytest inline and says "ship this" |
| Names **merge scope** (one PR, stack, doc-only) | Forbids assessor/recon as "already specified" |
| Says **out of scope** explicitly | Treats CI/workflow edits as trivial by default |

Good example (short):

> Objective: document host-neutral kickoff rules. Done when: PR on `main`, hooks tests green. Spec: assignment in Project store `docs/...`. Out of scope: roster slug changes. Branch: `supercook/coordinator-kickoff-hardening`.

Bad example (truncated):

> Turn 1: edit these six files, run pytest, open PR, ledger assessor skip because checklist below…

## By host

Same invariants as above; only typical spawn paths differ.

### Cursor chat (parent agent)

- **Who:** User `@supercook` or skill-loaded parent in the editor.
- **Spawn:** The named plugin `supercook-*` subagents when installed; else whatever spawn tool the session lists (often `Task`), launching a worker named `supercook-<role>` with the `agents/*.md` body and roster tags from intake.
- **Hooks:** `enforce_roster` may run when the plugin hooks are active; record `enforce_roster: yes|no` on the ledger capability line.
- **Parent job:** Read SKILL.md, run intake, launch assessor (or valid user-selected track), never treat the user's long message as permission to skip phase 1.

### Cursor Project coordinator

- **Who:** Coordinator assigns a worker; worker is still a Supercook parent for that run.
- **Spawn:** Often `CreateAgent` or typed subagents; **often no** `supercook-*` types in the worker VM roster.
- **Parent job:** Same pipeline. Coordinator checklists are worker *assignments*, not phase skips. Worker must not ship-pr or edit product code before intake + assessor unless track/tier says so.

### Cloud Agent on a user repo

- **Who:** Cloud worker on the customer's repository with the skill available.
- **Typed agents:** Present when the catalog lists `supercook-*` (installed plugin, or files mirrored into `~/.cursor/agents/` before the session started); otherwise record `supercook-agents: no`. Never vendor the agent files into the customer's repository to get them.
- **Where the spawn tool is:** a Cloud Agent can list `Task` inside a dynamic tool catalog namespace and not in its top-level tool list. Open that catalog and read the subagent types before recording `spawn: none`.
- **Spawn, when any spawn tool is listed:** launch the named subagent `supercook-<role>` through that tool, one launch per roster role, with the prompt = role and run tags, then the body of `agents/supercook-<role>.md`, then the brief. Set the tool's type or name field to `supercook-<role>` when it has one and accepts that name. Launch explorer, planner, test-designer, implementer, and verifier this way, not only the assessor. Prefer a same-machine option if the tool offers one; if the worker lands on its own VM, follow the separate-VM rule in [../agents.md](../agents.md#host-recipes).
- **Spawn, when nothing is listed:** record `spawn: none` and run each role inline from its agent file ([../agents.md](../agents.md#no-spawn-tool-run-roles-inline)). Do not wait for, guess, or invent a spawn tool that your own tool list does not show.
- **Extras:** Resolve models from repo `.supercook/models.md` when present; read plugin [../SKILL.md](../SKILL.md) on turn 1 even when the coordinator message is long.
- **Parent job:** Log `parent-host: cloud-agent` and `spawn:` when probed; launch the assessor as the first action after intake; run every phase through the recorded path; do not collapse to one-pass implement at any tier.

### Grok Bot, voice, and other entries

- **Who:** Any entry that loaded the same Supercook skill.
- **Spawn:** Whatever the host offers; invariants unchanged.
- **Parent job:** If the kickoff reads like a checklist, still run intake and assessor. No host-specific bypass documented here: only the invariants in this file and [../SKILL.md](../SKILL.md).

## Coordinators writing worker briefs

Prefer linking **objective**, **done-when**, **spec path**, and **branch** over inlining the implementation. Workers remain responsible for ledger rows that show assessor, explorer, planner, implementer, and verifier **launched** (or run `degraded: parent inline (spawn none)` when the worker has no spawn tool), or valid skips with assessor/tier reasons, not silent skips.

