# Merge

A PR exists and the user explicitly asked for it merged. The ask is the consent: do not ask again before merging. This track handles conflicts, comments, CI, the merge, and restacks. It does not run the review playbook's reviewer fan-out; that is `review and merge`.

Inside a live run, append these steps to its ledger. Cold, seed a ledger around the target PR and recover any UI contract and smoke evidence from the PR body.

## Steps

Copy these into the ledger verbatim, one block per PR on a stack.

```
- [ ] check out the PR; on a stack, state and log the full merge sequence and the rewrites it needs, per references/stacking.md (yours)
- [ ] read the state with `gh pr view <n> --json state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup`
- [ ] resolve conflicts, understanding both sides (yours)
- [ ] triage every comment, per references/merge.md (yours; a code fix is a supercook-implementer launch you check)
- [ ] fix in-scope CI failures and report the rest, per references/merge.md
- [ ] run the recorded tests before merging
- [ ] merge with the repo's default method once mergeable, green, and approved
- [ ] on a stack, restack the children, per references/stacking.md
```

## Rules

- A fix made here is a diff like any other: surgical, explained by file and consequence, its own commit.
- A comment asking for a feature is a new run; note it as a follow-up.
- Branch protection, missing approvals, and failing required checks are reported, never bypassed. They are the only things that stop a merge-ask run short of merged.

**Reply:** merged or not, and why; what was fixed on the way, naming the files.
