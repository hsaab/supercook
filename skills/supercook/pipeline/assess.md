# Phase 1: assess

You classify the task yourself, right after intake. It is a short read, not a launch: enough of the repo to be confident about scope, under five tool calls, then stop. Classify, do not plan. No approach, no file list, no implementation notes.

This verdict sizes the rest of the run, so it decides which phases run. It never decides who runs them. A `trivial` verdict removes recon, plan, and test-first; implement and verify are still worker launches.

User-selected tracks (`merge`, `implement-plan`, `review`) skip this phase. Mark the row `[~] skip: user-selected track`.

## Tier

Judge the risk of getting it wrong, not how long it takes to type.

**trivial**: one obvious change in one place, no behavior anyone depends on, and a wrong version would be caught immediately. A copy fix, a version bump, a log line, a comment.

**standard**: the common case. One area of the codebase, a handful of files, real behavior, and a wrong version would reach a user or another developer. Most bugs and most features land here.

A supplied design does not make copy-only work standard. It does make any change to
hierarchy, region membership or order, geometry, interactions, or responsive
behavior at least standard, because that work needs the UI contract, structure
tests, and a rendered smoke from [ui.md](ui.md).

Changes to GitHub Actions, other CI config, shared test plugins, or repo automation are not trivial by default. See [../playbooks/feature.md](../playbooks/feature.md#ci-workflows-and-test-harness-work).

**complex**: any one of these makes it complex.

- Three or more distinct areas or services change together.
- The right approach is genuinely unclear and reasonable engineers would disagree.
- A wrong choice is expensive to reverse (data shape, public interface, migration).
- The work touches security, auth, payments, or data integrity.

When torn between two tiers, pick the higher one only if you can name the specific risk. "It feels big" is not a reason, and neither is "it looks small" for the lower one.

## Track

- **bugfix**: something is broken and needs to work.
- **feature**: new or changed behavior.
- **investigation**: a question to answer. Nothing ships.
- **refactor**: same behavior, better structure. Explicitly no behavior change.
- **open-pr**: work already exists in the tree and needs to become a PR.

A "refactor" that changes behavior is a feature. Say so in `why`.

`merge`, `implement-plan`, and `review` are never inferred here. They are routed from the user's words before this phase, per [../SKILL.md](../SKILL.md#user-selected-track-routing). A task that will eventually produce a PR is a bugfix or a feature, not a merge.

## Big-change flag

`yes` when the work needs the user to agree on architecture before code gets written. That is true when it introduces or changes a data model, a public interface or API contract, a service boundary, an auth or permission model, or a migration.

`no` for everything else, including plenty of complex work. Complex means hard; big-change means the approach itself needs sign-off.

## The verdict

Write the four fields as the assess log line, check the assess row, and fill `tier:` and `track:` in the ledger header. On the investigation track, which has no ledger file, the same line goes in the todo list.

```
- <time> assess: tier: <trivial | standard | complex> | track: <bugfix | feature | investigation | refactor | open-pr> | big-change: <yes | no> | why: <one sentence>
```

The `why` line names concrete things: files, services, data, interfaces. Plain language, no em dashes.

Good: `why: touches the auth middleware plus both API gateways, and changes the session token shape.`

Bad: `why: this is a fairly complex change with wide-reaching implications.`

Then route to the playbook for `track` and launch the first worker it names.
