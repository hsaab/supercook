# UI source of truth

A supplied design is a contract, not inspiration. This guide is cross-cutting rather
than a phase. Load it at the first evidence of UI work or a supplied UI source.

## Contents

- [When this guide loads](#when-this-guide-loads)
- [Gate levels](#gate-levels)
- [Ledger fields](#ledger-fields)
- [Resolve a supplied design](#resolve-a-supplied-design)
- [The UI contract](#the-ui-contract)
- [Material deviations](#material-deviations)
- [Tests and parent guards](#tests-and-parent-guards)
- [Implementation evidence](#implementation-evidence)
- [Structural verification](#structural-verification)
- [Rendered smoke](#rendered-smoke)
- [Track exceptions](#track-exceptions)

## When this guide loads

Check for UI evidence in three places:

1. **Intake**: the task contains a design URL, screenshot, attachment, or layout spec.
2. **Recon**: the work touches a route, view, component, stylesheet, rendered content,
   or client state that changes what a user sees.
3. **Before verify**: inspect the diff. This catches trivial runs with no recon and
   open-pr runs whose work already exists.

Record the result in the ledger. If diff-time detection upgrades a run to the
contract gate after planning or test-first was skipped, reopen those rows. Resolve
the design, amend the plan or add the open-pr ledger contract, then add the missing
tests before implementation continues. When the current run already wrote the
source, restart that affected chunk from its pre-implementation snapshot so the new
tests fail first. Retrospective mode remains exclusive to open-pr.

## Gate levels

The levels are disjoint and contract takes precedence.

### Contract

Use contract when a supplied `ui-source` exists and a slice can change any of:

- hierarchy or region membership
- logical DOM order or visual order
- geometry, grouping, or repeated-item count
- interaction behavior
- responsive behavior

A design-backed layout change is at least standard tier, even when the diff looks
small.

### Light

Use light when either:

- `ui-change: yes` and no design was supplied, or
- the change cannot alter structure, such as copy, a label, one token, or one style
  value whose effect is local and known.

Light requires one rendered route check for a blank or broken result. It does not
add a UI contract, viewport matrix, or design-specific tests.

If a token or style value can alter wrapping, spacing, geometry, or responsive
behavior, it is not light. Use contract when a source exists, otherwise use the
normal journey tests plus a rendered check that covers the affected viewport.

## Ledger fields

Record three independent facts in the header:

```text
ui-change: yes | no
ui-source: figma <canonical URL> | screenshot <path> | spec <citation> | none
render-check: <browser or existing e2e command> | none
```

`ui-change` means a rendered surface moves. `ui-source` means someone supplied a
design to honor. `render-check` names how the real route can be exercised.

## Resolve a supplied design

The parent owns design retrieval. Resolve it after recon and again after the Design
Doc when phase 3 runs, because architecture prose can introduce a design URL that
intake did not contain.

- **Figma**: retain the canonical URL, `fileKey`, and every `nodeId`. Load the
  mandatory Figma design-to-code guidance, then call `get_design_context` for each
  independently designed node. Save or retain returned screenshots and assets as
  explicit run artifacts. Dashboard and rail nodes stay separate.
- **Screenshot**: read it and retain its path.
- **Spec**: retain a `file:line` citation or the exact quoted task text.

Produce a compact resolved brief covering hierarchy, logical order, visual order
per viewport, regions, geometry, responsive states, interactions, and visible
content. Pass that brief and its evidence to planning. Planners do not retrieve or
invent design details.

When the only source cannot be read, ask one focused question: provide a screenshot,
provide a written layout spec, or authorize proceeding without the unreadable
source. Record the answer. This is a sanctioned pause, not a dead run. Proceeding
without the source is allowed only when the ledger says the user authorized it.

## The UI contract

`plan.md` carries one global entry per independently designed screen. Slices refer
to entries by id and name the obligations they own.

```markdown
## UI source of truth

### UI-1 Dashboard
- source: figma <canonical URL>, file <fileKey>, node 26:2
- semantic order: Header, Summary, Highlights, Chart, Ranking, Low impact
- regions:
  - name: Highlights | locator: testid | anchor: insights-analyst-highlights | contains: three cards
  - name: Chart | locator: testid | anchor: insights-chart-total | contains: total chart
- rendered layout: header controls share a row; highlights and low-impact use 3 columns
- responsive: at 900px the chat moves below the dashboard
- interactions: date picker changes range; workflow links stay static
- deviations: none
- order test: UI-1 renders regions in design order
- smoke target:
  - start: pnpm dev
  - ready: http://localhost:5678/health
  - route: /insights/analyst
  - state: seeded overview for a community user
  - viewports: 1440x900, 900x900
  - checks: all regions contain data; layout and responsive behavior match above
```

Names come from Figma layer or section names, visible screenshot headings, or exact
spec language. Each region has a machine-readable locator and a literal `anchor`
that must appear in its tests. A role locator records the role in `locator` and the
accessible name in `anchor`.

Every contract-level slice includes:

```text
ui-contract: UI-1
ui-obligations: Highlights presence and count; Highlights before Chart
ui-order-test: owner | not-owner
```

The parent rejects a plan when a referenced entry is incomplete, a region has no
stable locator and anchor, responsive behavior has no viewport, slice ownership is
missing, or the smoke target cannot be executed or explicitly degraded. Exactly one
slice owns each contract's global order test, and its branch must contain every
region that test compares.

For dependent slices, the final smoke runs on the top branch. For independent
slices that compose one screen, create a temporary integration worktree or run the
final smoke after their changes share a branch. Never claim composed-page evidence
from separate branches.

Existing primitives constrain **how** a contracted region is built. They never
decide whether the region exists, where it sits, or which content it contains.
Copying a neighboring page's order is a material deviation, not reuse.

## Material deviations

A material deviation is an omitted or reordered region, changed hierarchy,
interaction, geometry, grouping, repeated-item count, or responsive behavior. A
product, security, or license constraint that prevents the design shipping as drawn
is also material.

- Authorization already present in the task counts as approval. Cite it.
- Otherwise present the deviation and pause before tests are written.
- A later material change reopens the approval gate.
- A component or token substitution that preserves the contract needs no approval.

The ledger records the design request, the deviation, the reason, and the approval.
Silent omissions are forbidden.

## Tests and parent guards

Contract tests assert what their environment can prove:

- every region is present by its locator
- repeated groups have the expected count
- elements belong to the correct semantic region
- logical DOM order matches `semantic order`
- required interactions work

Geometry, columns, widths, wrapping, and narrow-screen placement require an existing
browser test or the rendered smoke. Do not pretend a DOM assertion proves them, and
do not add a browser framework or pixel snapshots only for this gate.

Logical DOM order is the default. A source-approved visual reorder at a viewport is
recorded separately in `responsive`; CSS reordering that was not in the source is a
material deviation.

After the test designer returns, run fixed-string traceability checks for the
slice's owned anchors against its test paths or dedicated run-folder recipe. Run
the order-name check only on the order-test owner:

```bash
rg -F -- '<region anchor>' <test paths or verification-recipe path>
rg -F -- 'UI-1 renders regions in design order' <test paths or verification-recipe path>
```

Then confirm the named order test makes a real position comparison, is not skipped,
and fails for the intended missing behavior. Run it. The grep proves traceability;
the executed assertion proves semantics. A missing anchor or order assertion sends
the suite back just like a missing API journey.

On open-pr, source already exists. Run the same guard in
`retrospective-open-pr` mode, but record a pass or contract gap instead of claiming
the test failed first.

When no test runner exists, the test designer returns an executable structural
recipe. The parent writes it in the run folder, records its path in `plan.md` or the
open-pr ledger, and the verifier runs it. Missing tooling never turns the contract
into an unlogged skip.

## Implementation evidence

A contract-level implementer receives the contract entries, source locator,
resolved brief, visual evidence, owned obligations, and failing tests.

Before editing a view, it consumes the visual evidence. Direct
`get_design_context` access is optional because an implementation agent may not have
Figma tools; the parent's resolved brief plus retained screenshot is the fallback.

Its return includes one of:

```text
design-evidence: direct <node>
design-evidence: provided <artifact>
```

The parent rejects a contract-level return without that line. `skip: no layout
change` comes from the plan and is confirmed against the diff, never chosen by the
implementer.

## Structural verification

The verifier checks each slice's owned UI obligations against the plan, source,
tests, and diff. It reports:

```text
ui-contract: ok | mismatch: <specific gap>
```

A missing region, wrong order, missing test anchor, or unapproved deviation is
`verdict: gaps found`. Passing unrelated journeys cannot override it. The verifier
does not return `visual: ok`, because it did not render the route.

## Rendered smoke

Rendered smoke is a parent-owned ledger row per UI slice and once for the composed
page:

```markdown
- [ ] rendered smoke UI-1: /insights/analyst at 1440x900 and 900x900
```

At contract level, start the recorded app, wait for readiness, load the route in the
specified auth and seed state, exercise interactions, and compare visible content,
geometry, order, and responsive behavior to the contract. Record:

```text
rendered-smoke: pass | fail | blocked
```

A blank page, empty required seed, missing region, wrong order, wrong grouping, or
wrong responsive behavior is `fail`. A failure becomes a gap row and re-enters
implementation, then the smoke runs again.

When no renderer can load the target, use `[!]` with the route, attempted command,
and exact manual checks. Ask once for manual confirmation. If the user performs
those checks and confirms a pass, close the row as manual evidence. If the user
accepts delivery without that evidence, keep it sanctioned-blocked and name the
gap in the PR. With no answer, remain at the sanctioned pause. Static source
inspection or `curl` cannot pass a layout check.

At light level, load the changed route once in representative state and record
whether it rendered without a blank or broken result.

Delivery refuses to open a PR while any required smoke row is open or failed. A
contract smoke must be `pass` or explicitly sanctioned-blocked. The PR body carries
the design source, contract ids, deviations, contract summary, full smoke target,
tested head SHA, and latest result so a cold merge run can recover and rerun it.

## Track exceptions

- **Trivial**: copy-only work uses light. Before smoke, minimally resolve the changed
  view's route, start command, and representative state from repo evidence. A
  diff-time contract trigger reopens planning and test-first at standard tier.
- **Open PR**: reconstruct the UI contract in the ledger. Contract-level work uses
  the test designer in retrospective mode to add missing structural assertions,
  then verifies and smokes before delivery. Pre-edit evidence is not required for
  work that already existed.
- **Merge**: recover the contract and smoke evidence from the PR body. Require
  current smoke evidence when UI changed after the last recorded check.
- **Implement-plan**: same contract, structure tests, and rendered smoke as feature.
  Resolve the design before the optimizer runs. The optimizer completes contract
  fields from the resolved brief; it does not invent missing design detail.
- **Investigation**: report design mismatches with evidence, but create no gate or
  files.
