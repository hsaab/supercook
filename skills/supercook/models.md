# Model preferences

Every role ships with a model. The roster is a default, never a gate: a role whose model the session does not offer runs on `inherit` (the session model), and you can change any role at any point in a run.

## Where to edit

The parent merges files **per role**, highest tier wins, and the [roster choice](#choosing-a-roster) decides which tiers participate:

| Precedence | File | Purpose |
|---|---|---|
| 1 (wins) | `<workspace-root>/.supercook/models.md` | Optional override for this checkout. Commit it so cloud agents and other clones pick it up. Read under `roster:repo`. |
| 1 (wins) | `<plugin-root>/.supercook/models.md` | The roster committed in the supercook plugin repo. Read under `roster:supercook`. |
| 2 | `~/.supercook/models.md` | Your choices outside any repo. Read under `roster:repo`, `roster:machine`, and `roster:supercook`. |
| 3 | this file | The shipped default for every role. Read under `roster:repo`, `roster:machine`, and `roster:supercook`. |

Edit the home or repository file, not this one: a marketplace install lives in a cache directory the next update replaces. The home file does not exist until you create it:

```bash
mkdir -p ~/.supercook
curl -fsSL https://raw.githubusercontent.com/hsaab/supercook/main/skills/supercook/models.md -o ~/.supercook/models.md
```

Then keep only the roles you want to change; any role a higher file does not name falls through. Write `inherit` to put a role on the session model. The home `~/.supercook/` holds model choices; a repo's `.supercook/` holds run artifacts plus the optional override.

## Choosing a roster

A `roster:` word among the ask's leading modifiers picks which [files above](#where-to-edit) merge. `repo`, the default, merges the workspace file, your home file, and the shipped defaults; the ledger records `roster: repo`. `machine` skips the workspace file, so your home file decides per role and the shipped defaults fill every role it leaves out; the ledger records `roster: machine`. `roster:local` is an alias of `machine`, accepted without a warning; the ledger still writes `roster: machine`. `supercook` puts `<plugin-root>/.supercook/models.md` at tier 1 in place of the workspace file, with home and shipped filling roles it leaves out; the ledger records `roster: supercook`. The plugin root is the folder two above `skills/supercook/SKILL.md`. If that file is missing, say so once and run as `machine`. When the workspace is the supercook repo itself, `repo` and `supercook` may read the same file. Any other value is named once and runs as `machine`, so a typo never hands the run to a committed file. A `roster:` word later in the task stays task text; say once that it chose nothing.

## The roster

```
standard:           grok-4.7-high        # planner, test-designer, verifier
arena-a:            grok-4.7-high        # simplest viable plan
arena-b:            composer-2.5         # implementation-first plan
arena-c:            grok-4.7-high        # challenge assumptions and failure cases
plan-judge:         grok-4.7-high
implementer:        composer-2.5
explorer:           composer-2.5
reviewer:           grok-4.7-high        # bugbot, security-review, both thermo reviewers
review-implementer: composer-2.5         # finding fixes on the review track
```

Each role is independent: `reviewer` and `review-implementer` left on `inherit` do not fall through to `standard` or `implementer`. A `plan-optimizer` line from before 0.6.0 is ignored; the planner's supplied-plan mode uses `standard`.

## How a role becomes a model

1. Resolve the roster once, at ledger seed, merging per role across the files the [roster choice](#choosing-a-roster) names. A missing override file is normal and not worth mentioning.
2. Write the choice on the `supercook:` header line and one `models:` header line listing every key with its slug or `inherit`, so a resumed run reads them instead of re-resolving.
3. Pass the slug verbatim as the launch's `model` field; leave the field out for `inherit`. Never substitute a "nearest" model.
4. Do not pre-validate during a run; `/setup-supercook` checks the roster ahead of time. If a launch rejects the model, relaunch once without it, log `inherit`, and tell the user once. Never block a run on a model name.

**Mid-run changes** ("use opus for the implementer", "everything on the session model from here") win from the next launch on: update the `models:` line, log why, keep going. A roster choice mid-run, or on the ask that resumes a run, re-resolves every role: rewrite the `roster:` value and the `models:` line, and log it.

## Keep the arena diverse

The arena's value is three genuinely different lines of reasoning, so keep `arena-a`, `arena-b`, and `arena-c` on different model families when you override them. The shipped defaults span only two: `arena-a` and `arena-c` share `grok-4.7-high`, which still gives independent attempts, so a third family on one of them is the better override. `inherit` on one is fine if the session model differs from the other two.
