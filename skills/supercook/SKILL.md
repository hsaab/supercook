---
name: supercook
description: Orchestrated development workflow for any repository. Use for any development work (bugs, features, investigations, refactors, performance work, opening a PR from existing changes, driving an existing PR to merged, implementing a plan already written in plan mode) when the user invokes /supercook. Scales process to task risk, tracks every step in a ledger, plans complex work with a multi-model arena, tightens a supplied plan without an arena, writes user-journey tests before implementation, verifies with a fresh-context audit, and ships plain-language PRs under a reviewable size budget.
disable-model-invocation: true
---

# Supercook

## Contents

- [Principle 1: plain language tied to code and impact](#principle-1-plain-language-tied-to-code-and-impact)
- [The other principles](#the-other-principles)
- [Autonomy: host permissions first](#autonomy-host-permissions-first)
- [The pipeline](#the-pipeline)
- [Playbook routing](#playbook-routing)
- [Continuation protocol](#continuation-protocol)
- [Reference files](#reference-files)

## Principle 1: plain language tied to code and impact

This outranks everything else in this file. Get it wrong and the rest does not matter, because the user cannot tell whether the work is right.

Write like a sharp junior engineer who just joined this codebase, read the code carefully, and is telling a teammate what they found. That person has no shared history and no shorthand to fall back on, so they name the actual thing, in the actual file, and say what it means. That constraint is the point: it forces explanations to be checkable instead of confident.

Every explanation takes this shape:

> we changed `<function>` in `<file>` because `<specific reason grounded in the code>`, so `<the concrete consequence>`.

Worked example. Copy this register:

> we changed `handleWebhook` in `src/api/webhook.ts` because it still referenced a `retryCount` variable that the queue rewrite deleted, so any real webhook hitting that function would have thrown and taken the server down.

Rules that follow:

- **Always a file.** A path, plus the function or line when it helps. "Improved error handling" with nothing to look at is a defect, not a summary.
- **Always impact in real terms.** What breaks, what the user sees, what would have gone wrong. Never "for robustness" or "for maintainability".
- **No decoding required.** No jargon standing in for an explanation, no invented abbreviations (`cfg`, `impl`, `req`), no arrow chains where a sentence belongs.
- **Never pass through a subagent's summary as your own.** Read the diff, then restate it in this shape.
- **Never use an em dash or en dash.** Use a comma, a colon, parentheses, or two sentences.
- **Every surface.** Chat replies, ledger rows, plan summaries, PR bodies, commit messages, verifier verdicts, and every agent's returns contract.

## The other principles

1. **Ceremony scales with risk.** A one-line fix does not get an arena, a design doc, and a test matrix. See the tier rules in [pipeline/planning.md](pipeline/planning.md).
2. **Surgical diffs.** Change what the task needs. No opportunistic refactors, no drive-by renames, no reformatting untouched lines. A tempting cleanup gets reported, not done.
3. **Delegate atomic work with a clean context.** Each agent gets an objective, its inputs, an effort budget, boundaries, one done-when predicate, and a terse returns shape. See [agents.md](agents.md).
4. **The ledger is the memory.** Every phase and every skip is written down. Silent skips are banned. See [pipeline/ledger.md](pipeline/ledger.md).
5. **Own every diff.** Review each subagent's changes yourself before committing. Their summary is a claim, not evidence.
6. **Boundaries are enforced, not requested.** Every rule that matters has a parent-side check after the agent returns.
7. **Prove it on the real artifact.** Run the command, read the output, quote it. Never infer that tests pass. For UI work, the real artifact is the rendered route in a representative state, not only the unit suite.
8. **DRY and simple.** Name the data shape before the logic. Prefer the boring solution the next reader will follow.
9. **Match the codebase.** Its conventions beat your preferences. Read neighboring files first.

## Autonomy: host permissions first

A skill cannot override what runs it. Cursor's mode, tool approval prompts, user and workspace rules, repo policy, and branch protection all outrank these instructions. The rule is **continue whenever host permissions allow**, not absolute autonomy.

| Action tier | Behavior |
|---|---|
| Read-only (search, read, status, log, `gt log`, `gt merge --dry-run`) | Just run it. |
| Reversible writes (edit, commit, branch, worktree, push a run branch, `gt create`, `gt track`, `gt sync`, `gt restack`, `gt submit` on run-owned branches) | Run it, log a ledger row. If the host asks for approval, ask once with the reason, log the answer, keep going. `gt submit` force-pushes with lease on branches the run owns; treat that as this tier when the branch is ours, irreversible when it is not. |
| Irreversible (force-push, `gh pr merge`, `gt merge`, deploy, delete data, message other people) | Stop and ask every time. |

**One batched consent is allowed for a stack walk.** Phase 9 may state the full sequence of merges and branch rewrites once and take one yes for all of it; any deviation from the stated sequence re-asks. On the Graphite path, `gt merge --dry-run` is the sequence to state, and one yes covers `gt merge` plus the restacks it performs. See [pipeline/merge.md](pipeline/merge.md#stacked-prs).

**One batched consent is allowed for a stack walk.** Phase 9 may state the full sequence of merges and branch rewrites once and take one yes for all of it; any deviation from the stated sequence re-asks. See [pipeline/merge.md](pipeline/merge.md#stacked-prs).

Blocked is not the same as bypassable. Branch protection, failing required checks, and missing credentials get reported, never worked around.

**Sanctioned pauses**, each one a ledger row rather than a silent stall:

- Design Doc alignment on a big change.
- Ledger resume with several open candidates for this repo and branch.
- Missing credentials or access.
- A host-required approval.
- A genuine fork in intent where guessing would waste real work.
- An unreadable supplied UI source that needs a screenshot, written spec, or
  authorization to proceed without it.
- A UI route that cannot be rendered and needs manual confirmation or explicit
  acceptance of the missing visual evidence.
- Implement-plan intake that cannot pin a plan (none found, or several recent
  plan files with no clear match to this conversation).

**Scope modifiers are honored.** `/supercook plan only`, `no PR`, `no commits` and similar set the stop point up front. Reaching it counts as done.

**A merge ask extends the run instead of ending it.** `/supercook <task> and merge it` runs the pipeline through phase 9, and `/supercook merge <pr>` starts on the merge track with nothing to build. The ask also counts mid-run, after the user has seen the PR. Without it, phase 8 is the last phase. See [playbooks/merge.md](playbooks/merge.md).

**An implement-plan ask is user-selected, never inferred.** `/supercook use this plan` (the plan from this same chat), `/supercook implement <path>`, or an attached plan-mode file plus a request to carry it out starts on that track and skips the assessor. See [playbooks/implement-plan.md](playbooks/implement-plan.md).

**`keep ledger`** is the one modifier that adds rather than removes: it commits the ledger on the working branch so the run survives a different machine or a cloud agent. Off by default, because it puts run artifacts in your branch history. See [pipeline/ledger.md](pipeline/ledger.md#what-persistence-does-and-does-not-cover).

## The pipeline

Phases run in order. The assessor's verdict decides which ones are skipped, and the routed playbook can skip more. User-selected tracks (`merge`, `implement-plan`) route before the assessor runs.

| # | Phase | Guide |
|---|---|---|
| 0 | Intake: probe capabilities, decide the working tree, fix run identity, seed the ledger | [pipeline/intake.md](pipeline/intake.md) |
| 1 | Assess: tier, track, big-change flag | [agents.md](agents.md) |
| 2 | Recon: broad map, then targeted deep-dives, test paths and test command | [pipeline/recon.md](pipeline/recon.md) |
| 3 | Design Doc, big changes only | [pipeline/design-doc.md](pipeline/design-doc.md) |
| 4 | Plan: single planner, arena plus judge on complex work, or the optimizer on a supplied plan. Slices sized for review | [pipeline/planning.md](pipeline/planning.md) |
| 5 | Test-first: user-journey tests, committed before implementation | [pipeline/implementation.md](pipeline/implementation.md) |
| 6 | Implement: surgical chunks, parent guards, line accounting | [pipeline/implementation.md](pipeline/implementation.md) |
| 7 | Verify: fresh-context audit that runs the suite | [pipeline/verification.md](pipeline/verification.md) |
| 8 | Deliver: PR per slice, stack lifecycle, plain-language body | [pipeline/delivery.md](pipeline/delivery.md) |
| 9 | Merge: only on an explicit merge ask, never inferred | [pipeline/merge.md](pipeline/merge.md) |

**Phase 9 is opt-in.** Absent a merge ask, phase 8 ends the run at an open PR. A PR looking mergeable is not an ask.

**UI is a cross-cutting gate, not a phase.** Read
[pipeline/ui.md](pipeline/ui.md) at the first UI evidence in the task, recon, or
diff. A supplied design becomes the contract in `plan.md`; structure tests and a
rendered smoke enforce it. Late detection reopens any skipped planning or test rows.

**Tiers.** `trivial` collapses to implement plus verify, ledger still written. A
copy-only UI change keeps that light path; a supplied-design change to hierarchy,
order, geometry, interactions, or responsive behavior is at least standard.
`standard` runs recon, one planner, tests, implement, verify, deliver. `complex`
adds the arena and per-slice verification. The big-change flag inserts phase 3 at
any tier, including trivial, since a small diff can still change an interface
others depend on.

**Precedence when they disagree.** The tier collapse wins over a playbook's phase table. A playbook table describes its track at standard or complex tier, so a trivial bugfix runs implement plus verify even though `playbooks/bugfix.md` marks recon and plan as yes. The track still decides *what* the work is; the tier decides how much process it gets.

**The open-pr track is a routing exception.** Work already exists, so no tier sends
it through source implementation. It always verifies and delivers; tier only
changes recon depth. Contract-level UI can add retrospective structure tests, but
the implementer still does not run.

**The implement-plan track is a routing exception.** The user supplied a plan, so
the assessor does not run and the arena does not run. Process is standard-shaped:
recon scoped to the plan, the optimizer writes `plan.md`, then tests, implement,
verify, deliver. Tier collapse does not drop this to implement plus verify. Phase 3
is skipped; the supplied plan is the alignment. Optimizer dissent is reported, never
silently escalated to an arena.

**Phase 9 is a separate opt-in exception**, in both directions. No tier collapse
removes it once a merge was asked for, and no tier adds it when one was not. It
answers to the ask, not to the verdict.

## Playbook routing

Route on the assessor's `track`, except `merge` and `implement-plan`, which the user
selects directly. Copy the playbook's steps verbatim into the ledger.

| Track | When | Playbook |
|---|---|---|
| bugfix | Something is broken and needs to work | [playbooks/bugfix.md](playbooks/bugfix.md) |
| feature | New or changed behavior | [playbooks/feature.md](playbooks/feature.md) |
| investigation | A question to answer, nothing to ship | [playbooks/investigation.md](playbooks/investigation.md) |
| refactor | Same behavior, better structure | [playbooks/refactor.md](playbooks/refactor.md) |
| open-pr | Ship what is already in the tree | [playbooks/open-pr.md](playbooks/open-pr.md) |
| merge | A PR exists and the user asked for it merged | [playbooks/merge.md](playbooks/merge.md) |
| implement-plan | The user supplies a plan they already wrote | [playbooks/implement-plan.md](playbooks/implement-plan.md) |

## Continuation protocol

1. **Re-read the ledger before ending any turn.** Open rows mean keep working. Ending is allowed only when every row is checked or marked `skip: <reason>`, or the only blocker is a sanctioned pause that is written down. On the investigation track there is no ledger file, so the todo list is the record and this rule reads it instead.
2. **Done is a predicate, stated at intake.** Write it in the ledger header. A plateau is not a stop.
3. **Re-anchor before every launch and after every surprise.** Name the open ledger row the next action serves. Cannot name one? That is drift: log a course-correction row and get back on an open row. This is what stops an hour disappearing into one failing test while the plan sits forgotten.
4. **Report without stopping.** Send progress as a mid-turn note; do not end the turn to check in.
5. **Resume by identity.** A new, resumed, or compacted session reads the ledger matching this repo, branch, and run-id, then continues from the first open row. Never pick "the newest ledger".

## Reference files

- [models.md](models.md): which model each role uses, and how to change it.
- [agents.md](agents.md): the launch contract for all nine agents, the parent-side guard per role, and the fallback when the agents are not installed.
- [pipeline/ui.md](pipeline/ui.md): the contract and light UI gates, design
  resolution, structure-test guards, and rendered smoke.
- `pipeline/`: one guide per phase. Read the guide when the phase starts, not before.
- `playbooks/`: one per track. Most are routed at assess time. `merge` and `implement-plan` are user-selected.
