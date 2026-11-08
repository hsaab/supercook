# Model preferences

Repository roster for cloud agents and other shared checkouts. Cloud VMs typically have no `~/.supercook/models.md`, so this file is committed at tier 1 and wins per role over home and shipped defaults. See [skills/supercook/models.md](../skills/supercook/models.md) for the three-tier merge rules.

## The roster

```
standard:     claude-opus-5-5-high        # assessor, planner, test-designer, verifier
arena-a:      claude-fable-5-1-thinking-high
arena-b:      inherit                     # session model when gpt-5.6-sol-max is unavailable
arena-c:      claude-opus-5-5-high
plan-judge:   claude-opus-5-5-high
plan-optimizer: claude-opus-5-5-high
implementer:  grok-4.7-xhigh
explorer:     composer-2.5
reviewer:     composer-2.5                # bugbot, security-review, thermo reviewers on the review track
review-implementer: grok-4.7-xhigh
```
