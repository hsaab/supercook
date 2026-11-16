# Design doc

Runs only when the verdict says `big-change: yes`: a data model, public interface, service boundary, auth model, or migration changes, so architectural agreement has to come before code. It is always "design doc", never "TDD", so it cannot be confused with the test step.

## Full or lite

Ask once, saying what each costs:

> This changes the session token shape across two gateways, so it needs architecture sign-off first. Full design doc (15 sections, best when others will review it later) or lite (6 sections, enough to agree and move)?

Draft it as `design-doc.md` in the run folder.

**Full**: Summary; Background and context; Goals and non-goals; Requirements (functional and non-functional); High-level architecture (component diagram, data flow, where state lives); Data model; API and interface contracts; Tech stack and rationale; Alternatives considered; Security and privacy; Observability and failure handling; Testing strategy; Rollout plan (migrations, flags, rollback); Risks and open questions, with owners; Milestones.

**Lite**: Summary; Goals and non-goals; Architecture, with the diagram; Data model; API and interface contracts; Security. Add Alternatives considered whenever you rejected something a reviewer would ask about; it stops the same debate happening twice.

## Diagrams

Draw what is hard to hold in your head: the data flow, state ownership, the sequence when something fails. Lucid when its MCP responds, a canvas otherwise, a mermaid block at minimum. A box diagram of files nobody was confused about adds nothing.

## Approval

Present a short summary plus the diagram, not the whole markdown, and name the decision you want agreement on. Approval is a sanctioned pause: nothing is implemented while it is outstanding. Record it, for example `- [x] design doc (lite): approved 09:41`. If the user changes the approach, update the doc and log what changed; the plan builds on the approved version.

A design URL or screenshot in the doc is a UI source to resolve per [ui.md](ui.md), not visual approval.
