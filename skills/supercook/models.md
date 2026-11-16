# Model preferences

Every role ships with a model. The roster is a default, never a gate: a role whose model the session does not offer runs on `inherit` (the session model), and you can change any role at any point in a run.

## Where to edit

The parent merges the files in the chosen row **per role**: the first file that names a role decides it, and a missing file is skipped. The [roster choice](#choosing-a-roster) picks the row.

| Roster choice | Files, highest first |
|---|---|
| `roster:repo` (default) | `<workspace-root>/.supercook/models.md`, `~/.supercook/models.md`, this file |
| `roster:machine` | `~/.supercook/models.md`, this file |
| `roster:supercook` | `<plugin-root>/.supercook/models.md`, `~/.supercook/models.md`, this file |

`<workspace-root>/.supercook/models.md` is an optional override for this checkout; commit it so cloud agents and other clones pick it up. `~/.supercook/models.md` holds your choices outside any repo. `<plugin-root>/.supercook/models.md` is the roster committed in the supercook plugin repo. This file is the shipped default for every role.

Edit the home or repository file, not a file inside the installed plugin: a marketplace install lives in a cache directory the next update replaces. The home file does not exist until you create it:

```bash
mkdir -p ~/.supercook
curl -fsSL https://raw.githubusercontent.com/hsaab/supercook/main/skills/supercook/models.md -o ~/.supercook/models.md
```

Then keep only the roles you want to change; any role a higher file does not name falls through. Write `inherit` to put a role on the session model. The home `~/.supercook/` holds model choices; a repo's `.supercook/` holds run artifacts plus the optional override.

## Choosing a roster

A `roster:` word among the ask's leading modifiers picks a row of the [table above](#where-to-edit), and the ledger's `supercook:` line records it as `roster: repo`, `roster: machine`, or `roster: supercook`. `roster:local` is an alias of `machine`: accept it without a warning and record `roster: machine`; a ledger written by 0.8.0 that says `roster: local` also means `machine`. The plugin root is the folder two above `skills/supercook/SKILL.md`; if `<plugin-root>/.supercook/models.md` is missing, say so once and run as `machine`. Any other value is named once and runs as `machine`, so a typo never hands the run to a committed file. A `roster:` word later in the task stays task text; say once that it chose nothing.

## The roster

```
standard:           claude-opus-5-5-high       # planner, test-designer, verifier
arena-a:            claude-fable-5-2-high      # simplest viable plan
arena-b:            gpt-5.6-sol-max            # implementation-first plan
arena-c:            claude-opus-5-5-xhigh      # challenge assumptions and failure cases
plan-judge:         claude-opus-5-5-high
implementer:        claude-sonnet-5-5-high
explorer:           composer-2.5
reviewer:           claude-opus-5-5-high       # bugbot, security-review, both thermo reviewers
review-implementer: claude-sonnet-5-5-high     # finding fixes on the review track
```

Each role is independent: `reviewer` and `review-implementer` left on `inherit` do not fall through to `standard` or `implementer`. A `plan-optimizer` line from before 0.6.0 is ignored; the planner's supplied-plan mode uses `standard`.

## How a role becomes a model

1. Resolve the roster once, at ledger seed, merging per role across the files the [roster choice](#choosing-a-roster) names. A missing override file is normal and not worth mentioning.
2. Write the choice on the `supercook:` header line and one `models:` header line listing every key with its slug or `inherit`, so a resumed run reads them instead of re-resolving.
3. Pass the slug verbatim as the launch's `model` field; leave the field out for `inherit`. Never substitute a "nearest" model.
4. Do not pre-validate during a run; `/setup-supercook` checks the roster ahead of time. If a launch rejects the model, relaunch once without it, log `inherit`, and tell the user once. Never block a run on a model name.

**Mid-run changes** ("use opus for the implementer", "everything on the session model from here") win from the next launch on: update the `models:` line, log why, keep going. A roster choice mid-run, or on the ask that resumes a run, re-resolves every role: rewrite the `roster:` value and the `models:` line, and log it.

## Keep the arena diverse

The arena's value is three genuinely different lines of reasoning, so keep `arena-a`, `arena-b`, and `arena-c` on different model families when you override them. The shipped defaults use three different models, but `arena-a` and `arena-c` are both Claude models, so a non-Claude model on one of them is the better override. `inherit` on one is fine if the session model differs from the other two.
