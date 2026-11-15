# Assess

Classify the task yourself, before any worker launches. Read the repo for under five tool calls, then stop. Classify; do not plan. The verdict sizes the run, so it decides which steps are skipped. It never decides who runs them.

## Tier

Judge the risk of getting it wrong, not how long it takes to type.

- **trivial**: one obvious change in one place, no behavior anyone depends on, and a wrong version would be caught immediately. A copy fix, a version bump, a log line.
- **standard**: the common case. One area, a handful of files, real behavior, and a wrong version would reach a user or another developer.
- **complex**: any one of these: three or more areas or services change together; reasonable engineers would disagree on the approach; a wrong choice is expensive to reverse (data shape, public interface, migration); it touches security, auth, payments, or data integrity.

Changes to CI, workflows, shared test plugins, or repo automation are standard by default. When such work does collapse to trivial, log a one-line `trivial-collapse:` note naming the single hunk or file and why recon and plan add nothing; the verdict's `why:` does not count. A supplied design does not make copy-only work standard, but a change to hierarchy, order, geometry, interactions, or responsive behavior is at least standard. When torn, pick the higher tier only if you can name the specific risk.

## Track

- **bugfix**: something is broken and needs to work.
- **feature**: new or changed behavior.
- **investigation**: a question to answer. Nothing ships.
- **refactor**: same behavior, better structure. One that changes behavior is a feature; say so in `why`.
- **open-pr**: work already exists in the tree and needs to become a PR.

`merge`, `implement-plan`, and `review` are routed from the user's words, never inferred here.

## Big-change flag

`yes` when the user must agree on the architecture before code is written: a new or changed data model, public interface or API contract, service boundary, auth or permission model, or migration. Complex means hard; big-change means the approach itself needs sign-off.

## The verdict

Log it, and fill `tier:` and `track:` in the ledger header (on investigation, the line goes in the todo list):

```
- <time> assess: tier: <trivial | standard | complex> | track: <track> | big-change: <yes | no> | why: <one sentence naming files, services, data, or interfaces>
```

Good: `why: touches the auth middleware plus both API gateways, and changes the session token shape.` Bad: `why: a fairly complex change with wide-reaching implications.`

Then mark the tier's skips on the copied steps and launch the first worker step left open.
