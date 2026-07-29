# Model preferences

One file, one edit point. Every role below ships as `inherit`, which means it uses whatever model is driving the session. The suggested slugs sit commented next to each role. Uncomment one to opt into it.

## The roster

```
standard:     inherit    # suggested: claude-fable-5-thinking-max   (assessor, planner, test-designer, verifier)
arena-a:      inherit    # suggested: claude-fable-5-thinking-max
arena-b:      inherit    # suggested: gpt-5.6-sol-max
arena-c:      inherit    # suggested: claude-opus-5-thinking-max
plan-judge:   inherit    # suggested: claude-opus-5-thinking-max
implementer:  inherit    # suggested: cursor-grok-4.5-high-fast
explorer:     inherit
```

## How a role becomes a model

A slug written inside an agent file is not reliable. The model only takes effect when the parent passes it on the launch call, so the parent owns resolution:

1. **Read this file once**, at intake.
2. **Validate each uncommented slug** against the models the launch tool actually offers in this session.
3. **Valid slug**: pass it on every launch for that role.
4. **Anything else** (typo, unavailable on this plan, renamed): inherit the parent model, log one ledger row naming the role and the rejected slug, and keep going. Never guess at a "nearest" model. A wrong guess is worse than inheriting, and no dependable resolver exists.
5. **Never block a run on a model name.**

Uncommenting a line is your explicit request for that override. That is why nothing ships uncommented: picking models on your behalf, from a list your plan may not even carry, is not a default worth having.

## The one edit worth making

Give the three arena roles three **different** model families.

The arena is a cook-off: three agents plan the same complex task in parallel, then `supercook-plan-judge` merges or picks. Three contestants on one inherited model still give three independent attempts, but the value comes from genuinely different reasoning. Three families disagree in useful ways; three runs of one model mostly agree with themselves.

If you only change one thing in this file, change `arena-b` and `arena-c`.
