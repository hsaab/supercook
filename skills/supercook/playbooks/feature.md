# Playbook: feature

New or changed behavior. This is the track the full pipeline was designed around.

## Steps

Copy these into the ledger verbatim. A step that names a worker is that worker's launch; the reason after it is why the step is not yours.

```
- [ ] map the code the feature touches: supercook-explorer, one launch per area (its clean context reads more of the repo than yours should hold)
- [ ] plan.md names the data shape before any logic, and the user journeys this feature has to make work: supercook-planner, or the arena then supercook-plan-judge on complex tier (you check the plan, so you do not write it)
- [ ] tests, or an executable recipe without a runner, land before implementation: supercook-test-designer (it owns every test edit, so the implementer cannot bend the tests to fit)
- [ ] supplied UI design is resolved into a contract (yours) and pinned by structure tests (supercook-test-designer)
- [ ] implement slice by slice, each one shippable on its own: supercook-implementer, one launch per slice (you review its diff, so you do not write it)
- [ ] no opportunistic refactors in the diff: your scope guard on every implementer return
- [ ] the feature works end to end on the real artifact, not just in unit tests: supercook-verifier, a fresh launch (it did not write the code, so its pass is independent)
- [ ] every changed UI route passes its rendered smoke before delivery (yours)
```

## Phases

Every phase runs at standard and complex tier. Phase 3 depends on the big-change flag, and phase 4 uses the arena only on complex tier. A trivial feature collapses to implement plus verify, per the precedence rule in `SKILL.md`.

## CI, workflows, and test harness work

Changes to GitHub Actions, other CI config, shared pytest plugins, or repo automation are **feature** track at **standard** tier by default: recon, plan, test-first, implement, and verify still run. The kickoff may name workflow files; that naming is not a shortcut past phase 1 or the planner. Only a **trivial** verdict's tier collapse may drop recon and plan; another track skipping plan without collapse is not collapse. When that collapse drops recon and plan for this kind of work, log a one-line `trivial-collapse:` note in the ledger naming the single hunk or file and why recon and plan add no value. The verdict's `why:` line does not satisfy it. Other trivial work does not log `trivial-collapse:`.

## Name the data shape first

Before any logic, decide what the data looks like: the types, the schema, the payload, what is required and what is optional, what owns it.

Logic written before the shape is settled gets rewritten when the shape settles. Doing it in this order is also why the first slice is usually types and config: it is the cheapest thing to get right and the most expensive thing to get wrong.

Write the shape into `plan.md` explicitly so the implementer does not invent one.

## Journeys drive the tests

Name who uses this and what they are trying to do, in plain language, before thinking about assertions:

```
a new user signs up with an email that is already taken
an admin exports a report while a sync is running
a returning user hits the rate limit and sees a clear error
```

Those become the tests. Then add the realistic variations: bad input at a real entry point, empty state, the retry, permission denied. Skip the unlikely-input trivia and the tests for private helpers. See [../pipeline/implementation.md](../pipeline/implementation.md).

## Keep it DRY and simple

Reuse what exists. Before writing a helper, check whether the codebase already has one, and match its conventions if it does. Two implementations of the same idea is the thing that makes codebases hard to change later.

For a supplied UI design, reuse is a constraint on how a contracted region is
built. It is never permission to omit the region, change its content, or copy a
neighboring page's section order. Follow [../pipeline/ui.md](../pipeline/ui.md).

Simple beats clever every time. The next reader is the customer of this code, and often it is you in three months. Prefer the boring construction that reads top to bottom.

## Surgical scope

A feature is where scope creep is most tempting, because you are already in the files and you can see what else could be better.

- The refactor you noticed goes in the PR body as a note.
- The unrelated bug goes in the PR body as a note.
- The formatting of untouched lines stays untouched.

`plan.md` has an `out of scope` section for exactly this. Use it, so the reviewer can see the restraint was deliberate rather than accidental.

## Prove it end to end

A green unit suite is not proof the feature works. Exercise the real path: hit the endpoint, run the command, click through the flow, and read the actual output.

Put what you observed in the ledger and in the PR body. "Tests pass" is weaker evidence than "a request with 101 calls in a minute came back 429 with the retry-after header set".

For UI work, load each changed route in representative state and exercise the
changed flow. A contract-level slice checks its recorded viewports, regions,
geometry, responsive behavior, visible content, and interactions. A light slice
checks that the route is not blank or broken.
