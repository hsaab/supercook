# Plan

The plan is a contract, and its slices are PRs. Sizing happens here, because a finished monolithic diff is the worst place to learn it should have been three PRs.

## Who writes it

- **Standard tier**: one `supercook-planner` launch. An arena on standard work spends three model calls to confirm what one already knew.
- **Complex tier**: three `supercook-arena-runner` launches in parallel with an identical brief and the `arena-a`, `arena-b`, and `arena-c` models; only the model and candidate file differ, so the disagreements are the signal. Then one `supercook-plan-judge` launch reads the three candidate files and writes `plan.md`, merging or picking. Two candidates unsure about the same decision is the real risk; the plan has to face it.
- **implement-plan**: one `supercook-planner` launch with `mode: supplied-plan` and `user-plan.md`. It tightens the user's plan (stale paths, missing slice fields, oversized slices) and keeps the approach. A better architecture comes back as `dissent`, which you report; it never escalates to an arena.

## Slices

A slice is one shippable PR: it leaves the default branch working, carries its own verification, and a reviewer understands it without reading the next one. Cut along natural seams in dependency order (data shape, core logic, wiring, interface).

- **Budget: under 500 reviewable lines**, counted by `guard lines` (lockfiles, snapshots, vendored, and generated files excluded). A rewritten line counts twice, so rewriting a 300-line file is near the budget.
- Note any large lockfile or generated bundle the slice drags along; it does not count, but the reviewer still sees it.
- **Cohesion exception**: a slice stays whole when splitting would leave the default branch broken or unsafe in between (a migration and the code that writes the new column, a security fix and its call sites, a rename that only compiles once every reference moves). Write `exception: <reason>` on it and log it. A slice name like "one TDD slice" is not cohesion.
- Flag dependency chains longer than 3 slices; delivery caps a stack at 3 open PRs. Try cutting so more slices are independent.

When `acceptance.md` exists, `plan.md` has an `## Acceptance criteria` block, one line per criterion: `AC-1: <verbatim> -> slice <n>, <named test or check>`. A criterion no slice proves goes under `## Gaps` and is raised.

Contract-level UI adds the `## UI source of truth` entries and per-slice ownership from [ui.md](ui.md#the-ui-contract).

## Notify and continue

When `plan.md` lands:

1. Name slice 1's block after its slice, and add one slice block per further slice, per [ledger.md](ledger.md#seed).
2. Send the user the approach in a sentence, the slice list, and the total estimate. On implement-plan, add the changes from their plan and any dissent.
3. Keep working. The summary is a notification, not an approval gate. Only the sanctioned pauses stop here.
