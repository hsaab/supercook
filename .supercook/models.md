# Model preferences

Repository roster for cloud agents and other shared checkouts. From any workspace, `roster:supercook` reads this committed file first. Inside this plugin repo, `roster:repo` reads it as the workspace file. `roster:machine` skips it. See [skills/supercook/models.md](../skills/supercook/models.md#choosing-a-roster) for the merge rules and the roster choice.

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
