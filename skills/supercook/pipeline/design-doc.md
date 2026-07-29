# Phase 3: Design Doc (big changes only)

This phase runs only when the assessor sets `big-change: yes`. It is the one pause the skill itself introduces, and it exists because getting architectural agreement after the code is written is expensive and annoying for everyone.

It is called "Design Doc" throughout, never "TDD", so it never collides with test-driven development in phase 5.

## Contents

- [When it runs](#when-it-runs)
- [Ask full or lite](#ask-full-or-lite)
- [The full template](#the-full-template)
- [The lite template](#the-lite-template)
- [Diagrams](#diagrams)
- [Approval](#approval)

## When it runs

The big-change flag means the work introduces or changes a data model, a public interface or API contract, a service boundary, an auth or permission model, or a migration. Those are the decisions that are costly to reverse.

The flag is independent of tier. A standard-tier task can be a big change, and plenty of complex work is not. Inserting this phase is a ledger mutation: add the row, then continue.

## Ask full or lite

Ask once, in one line, and say what each costs:

> This changes the session token shape across two gateways, so it needs architecture sign-off first. Full design doc (all 15 sections, best when others will review it later) or lite (6 sections, enough to agree and move)?

Then draft it into the run folder as `design-doc.md`. Do not wait for an answer before starting to think; wait for it before writing the final structure.

## The full template

Preserved verbatim. Each line is a section heading plus what belongs in it.

```
Summary - one paragraph: what the app does, for whom, why it matters.
Background and context - the problem, prior art, why existing solutions fall short.
Goals and non-goals - explicit scope boundaries. Non-goals prevent scope creep and kill repeated debates.
Requirements - functional (features) and non-functional (latency targets, uptime, scale expectations, compliance).
High-level architecture - component diagram, data flow, where state lives. One good diagram beats pages of prose.
Data model - core entities, schema, ownership, retention.
API and interface contracts - endpoints, events, payloads between components and with external systems.
Tech stack and rationale - what you picked and why, not just what.
Alternatives considered - options you rejected and trade-offs. This section earns the most reviewer trust and saves relitigating decisions later.
Security and privacy - authn/authz model, data classification, threat surface.
Observability and failure handling - logging, metrics, alerting, what happens when dependencies fail.
Testing strategy - unit/integration/e2e split, what gets covered where.
Rollout plan - phases, migrations, feature flags, rollback path.
Risks and open questions - known unknowns, with owners.
Milestones - rough phases, not fake precision.
```

## The lite template

Six sections, for when the decision needs agreement but not a document others will review months later:

```
Summary - one paragraph: what changes and why it matters.
Goals and non-goals - explicit scope boundaries.
Architecture - what components change, how data flows, where state lives. Include the diagram.
Data model - entities and schema that change, plus ownership.
API and interface contracts - the endpoints, events, or payloads that change shape.
Security - authn/authz impact and anything sensitive this touches.
```

Add a seventh section, Alternatives considered, whenever you rejected something a reviewer would reasonably ask about. It is the cheapest way to stop the same debate happening twice, so reach for it rather than treating six as a limit.

## Diagrams

One good diagram beats pages of prose, which is why it is in both templates.

Try Lucid first when the MCP responds, since the result is editable and shareable. Fall back to a canvas otherwise. A mermaid block inside the doc is the floor, not the goal.

Draw the thing that is actually hard to hold in your head: the data flow, the state ownership, the sequence when something fails. A box diagram of files nobody was confused about adds nothing.

## Approval

Write the doc, then present it as a short summary plus the diagram, not as a wall of markdown pasted into chat. Name the specific decision you want agreement on.

Approval is a real gate. Do not start implementing while it is outstanding. Record it in the ledger with the time and which version was approved:

```
- [x] design doc (lite): design-doc.md approved (09:41)
```

If the user changes the approach in response, update the doc, log the change, and note what changed before moving on. The plan in phase 4 builds on the approved version, so the two must not drift.
