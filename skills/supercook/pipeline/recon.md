# Phase 2: recon

Learn the codebase without paying for it in context. Explorers read the source, the parent gets pointers.

## Fan-out

Scale the number of explorers to the shape of the task, not to its importance.

| Task shape | Explorers |
|---|---|
| One known file or function | 1, or none if the pointer is already obvious |
| One area, several files | 1 broad, then 1 targeted |
| Several areas or services | 1 broad, then 3 to 5 targeted, launched in parallel |

**Always start with the broad launch** on anything past trivial. It returns the stack, the layout, the conventions, the test command, and the test path patterns. The targeted launches then go deep on each area the work touches, and they run in parallel because they do not depend on each other.

Give each explorer a **question list**, not a topic. "Understand the auth system" produces a wandering essay. These produce pointers:

```
- Where does a request first hit auth, and what function name?
- Where is the session token created, and what fields does it carry?
- What happens today when the token is expired, and where is that decided?
- Is there existing rate limiting anywhere in this path?
```

## The two load-bearing outputs

The broad explorer must return both of these, and the parent must record them in the ledger header:

- **The test command.** The verifier is required to run it, and a wrong command means verification cannot happen.
- **The test path patterns.** The test-integrity guard matches changed paths against these. Get them wrong and either the guard misses a tampered test or it restores a legitimate source file.

Both must come from real evidence: the `scripts` block, a CI config, a test runner config, or an existing test file's own location and naming. Never infer them from the language.

## Keeping the context clean

The whole point is that the parent never reads the source it does not need to change.

- Explorer returns are pointers plus a note capped at 10 lines.
- No file dumps, no function bodies. A one or two line snippet is allowed only when the exact line is the answer.
- The parent reads full files later, during implementation review, and only the files in scope.

Record pointers in the ledger log rather than re-summarizing them in chat. The plan is where they get used.

## When recon is enough

On the investigation track, recon **is** the work. There is no plan, no test, and no PR. Answer the question with citations, explain it in plain language, and stop. See [../playbooks/investigation.md](../playbooks/investigation.md).

## When recon is not enough

If the planner or an arena runner comes back needing to explore, recon was too thin. Do not let the planning phase turn into an investigation. Launch another targeted explorer for the specific gap, log it, and re-run planning.
