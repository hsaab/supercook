# Implement

One `supercook-implementer` launch per slice, or per chunk when a slice has natural internal steps.

## The brief

- An explicit file list: the only files it may touch.
- The data shape, so it does not invent one.
- The failing tests (or recorded recipe) to turn green, by name, and the exact test command.
- Trivial work has no plan and no red test: the brief is the task text, the file scope, and the test command.
- Contract-level UI adds the evidence that slice owns, per [ui.md](ui.md#implementer-and-verifier).

## After every return, in order

1. **Run the implementer check** in [workers.md](workers.md#checks-after-each-return): `guard scope` with the slice's files, the test globs, `--since <tests sha>`, and `--fix`. Run it before committing, because `git restore --source=HEAD` cannot undo a committed test edit.
2. **Read the diff yourself.** The summary is a claim.
3. **Commit that unit** in the house style. The subject says what changed; the body says why it was wrong and what it means:

   ```
   Read webhook retry count from the queue record

   handleWebhook referenced a retryCount variable that the queue rewrite
   deleted, so every inbound webhook threw on its first line. The attempt
   count now comes off the queue record, which is where that state lives.
   ```

4. **Update the ledger** with `guard lines --base <slice base>` (reviewable and raw). The base is the default branch for an independent slice, or the previous slice's branch for a stacked one.

## Size

Past about 400 reviewable lines, close the slice at the next atomic boundary: verify it, open its PR, start the next slice. The budget and its one exception are in [plan.md](plan.md#slices). Estimates miss, and the running count is what catches it.

## When a chunk goes wrong

Two failed attempts at the same thing means stop. Revert the chunk, amend the plan, log the amendment, and launch again with the corrected scope. Stacking fixes on a bad foundation produces a diff nobody can explain.
