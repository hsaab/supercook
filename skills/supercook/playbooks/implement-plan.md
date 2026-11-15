# Implement plan

The user already wrote a plan. Tighten it, then build it. You do not classify the task, the arena never runs, and there is no design doc, because the user's plan is the alignment. Tier skips do not apply.

Find the plan, taking the first hit: a path in the ask; the plan from this chat (the newest file under `.cursor/plans/` or `~/.cursor/plans/` whose title matches, else the plan text in context); an attached file; pasted text. Nothing found, or several candidates with no clear match, is a sanctioned pause listing them.

## Steps

Copy these into the ledger verbatim, with the slice block once per slice per references/ledger.md. The reason after a worker is why the step is not yours.

```
- [ ] pin the plan verbatim as user-plan.md and echo its title (yours)
- [ ] map the files and areas the plan names, plus the test command and test paths: supercook-explorer, one launch per area (the planner needs ground truth, not your memory of the plan)
- [ ] plan.md tightens the user's plan without changing its approach: supercook-planner in supplied-plan mode, per references/plan.md (you check it against their plan)
- [ ] each slice in plan order, closed before the next starts (yours)
  - [ ] slice <n> tests land red before the code: supercook-test-designer, per references/test-first.md
  - [ ] slice <n> code: supercook-implementer, per references/implement.md (you check and commit its diff)
  - [ ] slice <n> matches its plan rows: supercook-verifier, a fresh launch, per references/verify.md
  - [ ] slice <n> PR opens (yours), per references/deliver.md
- [ ] the work lands end to end across every slice: supercook-verifier, a fresh launch, per references/verify.md
```

## Rules

- Never edit `user-plan.md`; later steps read it, not the chat.
- A file the plan names that no longer exists is a pointer for the planner, not a reason to redesign.
- The planner's `dissent` is reported in the plan summary, and the run continues on the user's plan.

**Reply:** what landed against each part of their plan, what the planner changed and why, and the PR links.
