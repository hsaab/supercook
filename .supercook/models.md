# Model preferences

Repository roster for cloud agents and other shared checkouts. Cloud VMs typically have no `~/.supercook/models.md`, so this file is committed at tier 1 and wins per role over home and shipped defaults. See [skills/supercook/models.md](../skills/supercook/models.md) for the three-tier merge rules.

## The roster

```
standard:           grok-4.7-high        # assessor, planner, test-designer, verifier
arena-a:            grok-4.7-high        # simplest viable plan
arena-b:            composer-2.5         # implementation-first plan
arena-c:            grok-4.7-high        # challenge assumptions and failure cases
plan-judge:         grok-4.7-high
plan-optimizer:     grok-4.7-medium
implementer:        composer-2.5
explorer:           composer-2.5
reviewer:           grok-4.7-high        # bugbot, security-review, both thermo reviewers
review-implementer: composer-2.5         # finding fixes on the review track
```
