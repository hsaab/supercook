# Playbook: investigation

A question to answer. Nothing ships.

## Steps

Track these in the todo list. This track has no ledger file, for the reason below.

```
- [ ] restate the question precisely, including what would count as an answer
- [ ] explore with citations, file and line for every claim
- [ ] answer in plain language, with the code as evidence
- [ ] say what is unknown rather than filling it with a guess
- [ ] give a recommendation when asked to choose, with the tradeoff named
```

## Phases

| Phase | Runs? |
|---|---|
| 0 intake | partly: probe capabilities and note the question. No worktree, no run folder, no ledger file, no exclude write |
| 1 assess | yes |
| 2 recon | yes, this is the whole job |
| 3 design doc | no |
| 4 plan | no |
| 5 test-first | no |
| 6 implement | no |
| 7 verify | no, but every claim needs a citation |
| 8 deliver | no |

Do not manufacture work that was not asked for. No plan, no tests, no PR, no "while I was in there" fixes. An investigation that leaves a diff behind was not an investigation.

## Nothing gets written

This track is read-only, and that includes the run folder. Do not create `.supercook/`, do not write a `ledger.md`, and do not touch git's exclude file. Writing files during a read-only request is a surprise, and surprises are what make people stop trusting an agent with their repo.

**The todo list is the ledger on this track.** The ledger's job is to hold the steps, record what was skipped, and tell the next turn what is still open. The todo list does all three, in memory, and the continuation protocol in `SKILL.md` reads it the same way. So no rule is being waived here: the record still exists, it just is not a file.

The tradeoff is honest and worth knowing: an in-memory record does not survive a session restart. That is acceptable, because an investigation ends with an answer in the conversation rather than a half-finished branch someone has to resume.

If the investigation turns into "and now fix it", that is a new run on a different track. Say so, then reroute, and that run gets a real ledger.

## Cite everything

Every claim carries a `file:line`. A statement about how the code behaves, without a pointer, is a guess wearing a suit.

```
src/auth/session.ts:88   token expiry is checked here, before the refresh path
src/api/middleware.ts:12 the middleware runs before that check, so an expired token
                         reaches the handler on the first request after expiry
```

## Answer in plain language

The answer is the deliverable, so it gets the house style at full strength: name the files, explain the mechanism, connect it to real consequence.

> Expired sessions get through on the first request after expiry. `src/api/middleware.ts:12` attaches the user before `src/auth/session.ts:88` checks expiry, so the handler sees a valid-looking user object. The second request fails correctly, because by then the refresh path has run and cleared the session. That is why this looks intermittent in the logs.

Lead with the answer. Supporting detail comes after, for whoever wants it.

## Say what you do not know

An honest gap is more useful than a confident guess, because the person reading it will make decisions based on what you said.

```
not found: no evidence of a rate limiter anywhere in the request path. Searched for
"rate", "throttle", "limit" across src/ and the middleware chain in src/api/.
```

## Recommendations

When asked to choose, choose. Give one recommendation, the specific reason, and the tradeoff you are accepting. A list of options with no opinion is not an answer to "which should we do".
