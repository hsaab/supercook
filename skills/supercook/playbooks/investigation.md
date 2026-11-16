# Investigation

A question to answer. Nothing ships, and nothing is written: no `.supercook/` folder, no ledger, no exclude entry, no diff. The todo list is the record, and the continuation rules read it the same way. Its first item names the [roster choice](../models.md#choosing-a-roster) and the explorer's model, since no ledger header holds them.

## Steps

Track these in the todo list. The reason after a worker is why the step is not yours.

```
- [ ] restate the question and what would count as an answer (yours)
- [ ] explore with a file:line for every claim: supercook-explorer, one launch per area, in parallel when there are several (its context reads the code so yours holds the question)
- [ ] open the cited lines and answer in plain language (yours)
- [ ] say what is unknown and where you looked
- [ ] when asked to choose, recommend one option and name the tradeoff
```

## Rules

- Every claim about the code carries a `file:line`. Without one it is a guess.
- Lead with the answer; detail comes after for whoever wants it.
- An honest gap beats a confident guess: `not found: no rate limiter in the request path; searched src/ and the middleware chain in src/api/`.
- A thin explorer return gets a relaunch with a sharper question list, not your own scan.
- If it turns into "and now fix it", that is a new run on another track, with a real ledger.

**Reply:** the answer first, the mechanism with citations, then what is unknown. For example: "Expired sessions get through on the first request after expiry. `src/api/middleware.ts:12` attaches the user before `src/auth/session.ts:88` checks expiry, so the handler sees a valid-looking user."
