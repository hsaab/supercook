# Model preferences

Every role ships with a model. The roster is a default, never a gate: a role whose model the session does not offer runs on `inherit` (the session model), and you can change any role at any point in a run.

## Where to edit

The parent merges three files **per role**, highest tier wins:

| Precedence | File | Purpose |
|---|---|---|
| 1 (wins) | `<workspace-root>/.supercook/models.md` | Optional override for this checkout. Commit it so cloud agents and other clones pick it up. |
| 2 | `~/.supercook/models.md` | Your choices outside any repo. |
| 3 | this file | The shipped default for every role. |

Edit the home or repository file, not this one: a marketplace install lives in a cache directory the next update replaces. The home file does not exist until you create it:

```bash
mkdir -p ~/.supercook
curl -fsSL https://raw.githubusercontent.com/hsaab/supercook/main/skills/supercook/models.md -o ~/.supercook/models.md
```

Then keep only the roles you want to change; any role a higher file does not name falls through. Write `inherit` to put a role on the session model. The home `~/.supercook/` holds model choices; a repo's `.supercook/` holds run artifacts plus the optional override.

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

1. Resolve the roster once, at ledger seed, merging per role across the three files. A missing override file is normal and not worth mentioning.
2. Write one `models:` header line listing every key with its slug or `inherit`, so a resumed run reads it instead of re-resolving.
3. Pass the slug verbatim as the launch's `model` field; leave the field out for `inherit`. Never substitute a "nearest" model.
4. Do not pre-validate. If a launch rejects the model, relaunch once without it, log `inherit`, and tell the user once. Never block a run on a model name.

**Mid-run changes** ("use opus for the implementer", "everything on the session model from here") win from the next launch on: update the `models:` line, log why, keep going.

## Keep the arena diverse

The arena's value is three genuinely different lines of reasoning, so keep `arena-a`, `arena-b`, and `arena-c` on different model families when you override them. `inherit` on one is fine if the session model differs from the other two.
