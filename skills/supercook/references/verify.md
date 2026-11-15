# Verify

Done is a gate, and this is the gate. Launch `supercook-verifier` fresh, with the contract and the diff and nothing about how the code was built. A verifier that watched the code get written can be talked into believing it works.

## The contract it checks against

- `plan.md` on standard and complex tier. A missing `plan.md` there is `verdict: gaps found` and reopens the plan step.
- The task text and the ledger's `done:` on trivial tier.
- The ledger's `open-pr scope` baseline on the open-pr track.
- `acceptance.md`, when it exists, and the recipe path plus its recorded hash when a recipe replaced tests.

## When it runs

On multi-slice work, before each slice's PR opens, against that slice's plan rows and diff. Then a final pass over the whole plan, so nothing falls between slices. Verifying only at the end means shipping three PRs before finding out slice 1 missed half its plan.

## After it returns

- Fresh output is quoted and every plan row is landed, missing, or partial with a file citation. No output means a relaunch, not acceptance; this is the one place leniency defeats the whole arrangement.
- `tests: MODIFIED` means a test changed outside the test designer's commit, so the implementer check did not run, or ran after a commit. Restore the file, log it, and find out which.
- Contract-level UI also needs `ui-contract: ok`, then your rendered smoke per [ui.md](ui.md#rendered-smoke).

## The gap loop

`verdict: gaps found` turns each gap into a new ledger row naming the file and the missing behavior. Launch the implementer on that gap, not the whole slice, then verify again. A chunk that fails the verifier twice gets reverted and planned again rather than patched a third time.

`verdict: blocked` means the recorded command could not run at all. Report the command and the error, fix the environment if it is in scope, and run it again. Never substitute a different command that happens to succeed.

The step closes on `verdict: pass` with quoted output. Not "the tests looked green earlier".
