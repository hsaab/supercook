# Playbook: implement-plan

The user already wrote a plan. Tighten it, then run the standard pipeline without the arena.

## Trigger and entry

**Trigger: the user asked to implement a plan they already wrote.** In the invocation (`/supercook use this plan`, `/supercook implement this plan`, `/supercook implement .cursor/plans/rate-limiting.md`), or by attaching a plan-mode markdown file and asking supercook to carry it out. Nothing else selects this track. The assessor never routes here on its own.

The common flow is plan mode, then `/supercook use this plan` in the same chat, with no path. A path is optional.

**This track skips the assessor.** Process is standard-shaped: recon, optimizer, tests, implement, verify, deliver. The arena never runs, even when the supplied plan would have been complex. Phase 3 is skipped; the supplied plan is the alignment. Phase 9 merge stays opt-in, same as everywhere else.

Tier collapse does not drop this track to implement-plus-verify. A supplied plan still needs recon (so the optimizer can check it against the code) and slice-shaped tests.

If the optimizer's `dissent` line names a materially better approach, report it in the changes summary and keep going on the user's plan. Do not silently escalate to an arena.

## Plan intake

Resolve the plan source before recon. Take the first hit in this order:

1. **An explicit path in the invocation.** The user named the file. Read that path.
2. **The plan already in this conversation.** Plan-mode plans land as files under `.cursor/plans/` (workspace) or `~/.cursor/plans/`, and the plan content is usually also visible in the conversation. Prefer reading the plan file when it can be identified: the most recently modified plan file whose title matches the conversation's plan. Fall back to the plan text in context when a file cannot be identified.
3. An attached markdown file.
4. Plan content pasted in the message.

Nothing found is a sanctioned pause asking for the plan, not a guess. Ambiguity (several recent plan files, none clearly this conversation's) also pauses with the candidates listed, since implementing the wrong plan wastes the whole run.

Once the run folder exists, copy the chosen source verbatim into it as `user-plan.md` before recon or the optimizer run. Echo the plan title in one line so the user can catch a wrong pick. Later phases read that pinned artifact, never chat scrollback, and never edit `user-plan.md`.

## Steps

Copy these into the ledger verbatim.

```
- [ ] pin the supplied plan as user-plan.md and echo its title
- [ ] recon the files and areas the plan names, plus the test command
- [ ] optimizer writes plan.md without changing the user's approach
- [ ] tests, or an executable recipe without a runner, land before implementation
- [ ] supplied UI design is resolved into a contract and pinned by structure tests
- [ ] implement slice by slice, each one shippable on its own
- [ ] no opportunistic refactors in the diff
- [ ] the work lands end to end on the real artifact, not just in unit tests
- [ ] every changed UI route passes its rendered smoke before delivery
```

## Phases

| Phase | Runs? |
|---|---|
| 0 intake | yes. Pin `user-plan.md` once the run folder exists. Echo the plan title |
| 1 assess | no. The track is user-selected; skip the assessor |
| 2 recon | yes, scoped to the files and areas the plan names, plus the test command and test path patterns |
| 3 design doc | no. The supplied plan is the alignment |
| 4 plan | yes, `supercook-plan-optimizer` only. No planner, no arena, no judge |
| 5 test-first | yes |
| 6 implement | yes |
| 7 verify | yes |
| 8 deliver | yes |
| 9 merge | only when the user asked for the PR merged too |

Mark phase 1 and phase 3 `skip: user-selected implement-plan; supplied plan is the alignment` when the ledger is seeded. Silent skips are banned.

## Recon is scoped by the plan

Do not start with a broad map of the whole repo. Launch explorers against the files, functions, and areas `user-plan.md` names. The point is to give the optimizer ground truth so it can correct stale paths, not to reopen the approach.

The broad-launch returns still apply: the test command and the test path patterns must come back from evidence, because later phases depend on both. For UI work, also return the render setup from [../pipeline/recon.md](../pipeline/recon.md). Unknown facts say `not found`.

If a named file in the plan is gone, that is a pointer the optimizer must see, not a reason to redesign.

## Optimizer, then the rest of standard

Phase 4 launches `supercook-plan-optimizer` with `user-plan.md`, the recon pointers, the resolved UI brief when one exists, and the slice budget. It writes `plan.md`. See [../pipeline/planning.md](../pipeline/planning.md#supplied-plan-the-optimizer).

When `plan.md` lands, notify and continue as that guide says, and include the optimizer's `changes` list (or `no changes beyond slicing`) plus any `dissent` line. Then phases 5 through 8 are the standard pipeline: [../pipeline/implementation.md](../pipeline/implementation.md), [../pipeline/verification.md](../pipeline/verification.md), [../pipeline/delivery.md](../pipeline/delivery.md).

## UI is unchanged

A supplied design in the plan still triggers [../pipeline/ui.md](../pipeline/ui.md). Resolve it before the optimizer runs. Material deviations still need approval. Structure tests and rendered smoke still gate delivery.
