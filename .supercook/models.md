# Model preferences

Repository roster for cloud agents and other shared checkouts. Cloud VMs typically have no `~/.supercook/models.md`, so this file is committed at tier 1 and wins per role over home and shipped defaults, unless the run uses `roster:local`. See [skills/supercook/models.md](../skills/supercook/models.md#choosing-a-roster) for the merge rules and the roster choice.

## The roster

```
standard:           cursor-grok-4.6-xhigh  # planner, test-designer, verifier
arena-a:            cursor-grok-4.6-xhigh  # simplest viable plan
arena-b:            composer-2.5           # implementation-first plan
arena-c:            cursor-grok-4.6-xhigh  # challenge assumptions and failure cases
plan-judge:         cursor-grok-4.6-xhigh
implementer:        composer-2.5
explorer:           composer-2.5
reviewer:           cursor-grok-4.6-xhigh  # bugbot, security-review, both thermo reviewers
review-implementer: composer-2.5           # finding fixes on the review track
```
