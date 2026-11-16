# UI work

A supplied design is a contract, not inspiration. Load this at the first sign of UI work: a design URL, screenshot, or layout spec in the task; recon finding a route, view, component, or stylesheet that changes what a user sees; or UI files in the diff before verify. Late detection reopens any plan or test step a tier skip removed. When the run already wrote the source, restart that chunk from its pre-implementation snapshot so the new tests fail first.

## Level

- **Contract**: a design was supplied and a slice can change hierarchy, region order, geometry, grouping, repeated-item count, interactions, or responsive behavior. At least standard tier.
- **Light**: UI changes with no supplied design, or a change that cannot alter structure (copy, a label, one local style value). One rendered check of the route for a blank or broken result; no contract.

A token or style value that can change wrapping, spacing, or layout is not light. Record `ui-change: yes | no`, `ui-source: figma <url> | screenshot <path> | spec <citation> | none`, and `render-check: <browser or e2e command> | none` in the ledger header.

## Steps this adds

```
- [ ] resolve the design into a brief before planning (yours)
- [ ] rendered smoke per UI slice, then once for the composed page (yours)
```

The first explorer also returns render facts: the start command, readiness signal, route, seed or auth state, viewport mechanism, and teardown, each with evidence or `not found`. A guessed port is not evidence.

## Resolve the design

You retrieve it, after recon and again after a design doc. Planners never retrieve or invent design detail.

- **Figma**: keep the URL, `fileKey`, and every `nodeId`; load the Figma design-to-code skill, call `get_design_context` per independently designed node, and keep the screenshots as run artifacts.
- **Screenshot**: keep its path. **Spec**: keep a `file:line` or the quoted task text.

Write a compact brief: hierarchy, logical order, visual order per viewport, regions, geometry, responsive states, interactions, visible content. An unreadable source gets one question (a screenshot, a written spec, or authorization to proceed without it) as a sanctioned pause.

## The UI contract

`plan.md` carries one entry per independently designed screen:

```markdown
## UI source of truth
### UI-1 Dashboard
- source: figma <url>, file <fileKey>, node 26:2
- semantic order: Header, Summary, Highlights, Chart, Ranking
- regions:
  - name: Highlights | locator: testid | anchor: insights-analyst-highlights | contains: three cards
- rendered layout: header controls share a row; highlights use 3 columns
- responsive: at 900px the chat moves below the dashboard
- interactions: date picker changes range
- deviations: none
- order test: UI-1 renders regions in design order
- smoke target: start `pnpm dev`, ready http://localhost:5678/health, route /insights/analyst, state seeded community user, viewports 1440x900 and 900x900
```

Region names come from Figma layers, screenshot headings, or spec language, and each has a locator plus a literal `anchor` its tests must contain. Each UI slice adds `ui-contract: UI-1`, `ui-obligations: <the regions and order it owns>`, and `ui-order-test: owner | not-owner`. Exactly one slice owns each contract's order test, and its branch must contain every region the test compares. Reject a plan missing any of this.

Existing components decide how a region is built, never whether it exists or where it sits. **Material deviations** (an omitted or reordered region, changed hierarchy, interaction, geometry, grouping, or responsive behavior) need approval before tests freeze them: cite authorization in the task, or ask and pause. A component swap that keeps the contract needs none.

## Tests and the anchor check

Contract tests assert what the DOM can prove: each region by its locator, repeated-item counts, semantic containment, logical DOM order (on the owner only), and interactions. Columns, widths, wrapping, and narrow-screen placement need an existing browser test or the rendered smoke; do not add a browser framework or pixel snapshots for this. After the test designer returns:

```bash
rg -F -- '<region anchor>' <test paths or recipe>                   # each owned anchor
rg -F -- 'UI-1 renders regions in design order' <test paths or recipe>   # order-test owner only
```

Every search must match, and the order test must compare real element positions, not be skipped, and fail for the missing order. A gap goes back to the test designer.

## Implementer and verifier

The implementer brief carries the contract entry, the source locator, the brief, the retained screenshot, and the slice's obligations. Its return must include `design-evidence: direct <node>` or `design-evidence: provided <artifact>`; reject one without it. The verifier returns `ui-contract: ok | mismatch: <gap>`; a mismatch is `gaps found` even when every other journey passes. It never claims `visual: ok`, because it did not render anything.

## Rendered smoke

Yours, per UI slice and once for the composed page (on the top branch of a stack, or a temporary integration worktree for independent slices). Start the app, wait for readiness, load the route in the recorded state, exercise the interactions, and compare content, order, geometry, and responsive behavior at each viewport. Record `rendered-smoke: pass | fail | blocked` with the head SHA.

- A blank page, missing region, wrong order, or wrong responsive behavior is `fail`: a gap row, a fix, and the smoke again.
- When nothing can render the route, mark the row `[!]` with the route, the command tried, and the exact manual checks, and ask once. A user-confirmed manual pass closes it; delivery without the evidence must name the gap in the PR. Reading the source or `curl` never passes a layout check.
- No PR opens with a smoke row open or failed. The PR body carries the source, contract ids, deviations, smoke target, tested head, and result, so a cold merge can rerun it when the head changed.

## Track notes

- **Trivial** copy work is light; resolve the route and start command from the repo before the smoke.
- **Open PR**: write the contract in the ledger; the test designer adds missing structure tests in `characterization` mode.
- **Merge**: recover the contract and smoke from the PR body, and rerun the smoke when the head moved past it.
- **Investigation**: report design mismatches with evidence; add no steps or files.
