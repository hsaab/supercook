# Kickoff messages and parent invariants

Supercook runs on more than one host. The parent may be a Cursor chat agent, a Project worker, a Cloud Agent checkout, or another entry that loaded the skill. Spawn tools differ (`Task`, `CreateAgent`, host `Subagent`, or typed `supercook-*` agents). The rules below do not.

## Non-negotiables (every host)

These apply whether the user invoked `/supercook` in chat or a coordinator pasted a worker brief.

1. **Turn 1:** Read [../SKILL.md](../SKILL.md) in full before intake edits, assessor skip logic, or any repo change.
2. **Intake then assessor:** Phase 0 and phase 1 complete (or a user-selected track that legitimately skips assessor per [../SKILL.md](../SKILL.md)) before implementation, workflow, or delivery edits.
3. **Checklist is not a plan:** A pasted file list, YAML block, pytest recipe, or step-by-step implement list is a *spec pointer* at most. It does not replace recon, planner output in `plan.md`, test-first rows, verifier, or ledger phases.
4. **Fallback is still delegation:** When `supercook-*` agents are missing, phases 1, 2, 4, 6, and 7 still run through an equivalent worker/subagent launch using `agents/supercook-<role>.md` as the prompt body (see [../agents.md](../agents.md)). The parent orchestrates and guards; it does not solo-implement on **standard** or **complex** tier unless assessor classified **trivial** and tier collapse applies.
5. **Invalid ledger skip:** `skip: user checklist`, `skip: coordinator spec`, or `skip: agents not installed` without assessor-approved trivial collapse is never valid on standard/complex work.

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
- **Spawn:** Plugin `supercook-*` subagents when installed; else `Task` with `agents/*.md` body and roster tags from intake.
- **Hooks:** `enforce_roster` may run when the plugin hooks are active; record `enforce_roster: yes|no` on the ledger capability line.
- **Parent job:** Read SKILL.md, run intake, launch assessor (or valid user-selected track), never treat the user's long message as permission to skip phase 1.

### Cursor Project coordinator

- **Who:** Coordinator assigns a worker; worker is still a Supercook parent for that run.
- **Spawn:** Often `CreateAgent` or typed subagents; **often no** `supercook-*` types in the worker VM roster.
- **Parent job:** Same pipeline. Coordinator checklists are worker *assignments*, not phase skips. Worker must not ship-pr or edit product code before intake + assessor unless track/tier says so.

### Cloud Agent on a user repo

- **Who:** Cloud worker on the customer's repository with the skill available.
- **Spawn:** `CreateAgent` or `Task` per host catalog.
- **Extras:** Resolve models from repo `.supercook/models.md` when present; read plugin [../SKILL.md](../SKILL.md) on turn 1 even when the coordinator message is long.
- **Parent job:** Log `parent-host: cloud-agent` when probed; delegate phases; do not collapse to one-pass implement on standard/complex.

### Grok Bot, voice, and other entries

- **Who:** Any entry that loaded the same Supercook skill.
- **Spawn:** Whatever the host offers; invariants unchanged.
- **Parent job:** If the kickoff reads like a checklist, still run intake and assessor. No host-specific bypass documented here: only the invariants in this file and [../SKILL.md](../SKILL.md).

## Coordinators writing worker briefs

Prefer linking **objective**, **done-when**, **spec path**, and **branch** over inlining the implementation. Workers remain responsible for ledger rows that show **launched** assessor, explorer, planner, and verifier (or valid skips with assessor/tier reasons), not silent skips.

