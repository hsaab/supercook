# Model preferences

Every role below ships with a model already set. A role whose model your session does not offer falls back to `inherit`, which means it uses whatever model is driving the session. The roster is a default, never a gate: nothing blocks a launch on its model, and you can change any role's model at any point in a run.

## Where to edit

Three files can define the roster. The parent reads all three and merges **per role**, highest tier wins:

| Precedence | File | Purpose |
|---|---|---|
| 1 (wins) | `<workspace-root>/.supercook/models.md` | Optional override for this checkout. Names a role here and only that role changes. |
| 2 | `~/.supercook/models.md` | Your choices outside any repo. Wins for any role the repository file does not name. |
| 3 | this file (`skills/supercook/models.md`) | Shipped default. A model for every role when neither override names it. |

**Edit the home file or the repository file, not this one**, unless you cloned the repo into `~/.cursor/plugins/local/`. A marketplace install lives in a commit-pinned cache directory that the next plugin update replaces with a fresh one, so an edit made there is stranded the moment a new version lands. The home and repository paths are outside all of that.

The home file does not exist until you create it:

```bash
mkdir -p ~/.supercook
curl -fsSL https://raw.githubusercontent.com/hsaab/supercook/main/skills/supercook/models.md -o ~/.supercook/models.md
```

The repository file is optional: create `<workspace-root>/.supercook/models.md` with the same fenced roster shape when this checkout should pin models for your session. That path lives under repo `.supercook/`; run artifacts there stay untracked, but you can commit `models.md` so cloud agents and other clones pick up tier 1 without a home file.

Then change the roles you want and delete the lines you do not. Any role a higher file does not name falls through to the next tier, so a home file naming two roles changes exactly those two only when the repository file does not name those roles. Write `inherit` on a role to put it back on the session model.

Do not confuse `~/.supercook/` with the `.supercook/` folder inside a repo. The home one holds your personal model choices. The repo `.supercook/` folder holds run artifacts for that checkout **and** may hold an optional `models.md` override that wins over home and shipped for roles it names.

## The roster

```
standard:           grok-4.7-high        # assessor, planner, test-designer, verifier
arena-a:            grok-4.7-high        # simplest viable plan
arena-b:            composer-2.5         # implementation-first plan
arena-c:            grok-4.7-high        # challenge assumptions and failure cases
plan-judge:         grok-4.7-high
plan-optimizer:     grok-4.7-medium
implementer:        composer-2.5
explorer:           composer-2.5
reviewer:           grok-4.7-high        # bugbot, security-review, both thermo reviewers
review-implementer: composer-2.5         # finding fixes on the review track
```

The two review-track roles are independent of the rest, like every role here: `reviewer` covers the external reviewer launches on the review track (up to four per PR, fewer when hosted results are reused), `review-implementer` covers the finding-fix launches there, and leaving either on `inherit` does not fall through to `implementer` or `standard`.

Every slug above was checked against a real model list rather than guessed. An unresolvable slug costs you a fallback to `inherit` for that role, so a plausible-looking slug that does not exist only hides which model ran.

## How a role becomes a model

A slug written inside an agent file is not reliable. The model only takes effect when the parent passes it on the launch call, so the parent owns resolution:

1. **Read all three roster files once, at intake**, merging per role: `<workspace-root>/.supercook/models.md`, then `~/.supercook/models.md`, then this file. A missing file at either override tier is the normal case, not an error, and never worth a word to the user.
2. **Merge per role, not per file.** For each roster key, the repository value wins over the home value, which wins over the shipped value. A repository file that sets only `arena-b` changes exactly `arena-b`.
3. **Write one `models:` ledger header** listing every roster key with its slug or plain `inherit`. A resumed run reads that line instead of re-resolving.
4. **Pass the slug verbatim** as the `model` field on each launch. Omit the field for a role that is `inherit`. Never substitute a "latest" or "nearest" model.
5. **Do not pre-validate slugs.** If a launch rejects the model, the retry ladder in [SKILL.md](SKILL.md#start-here-the-launch-rule) drops the `model` field and relaunches. The launch row records the model actually used (`inherit` when dropped), and the user hears about it once.
6. **Never block a run on a model name.**

### Changing a model mid-run

The user can change a model at any point: "use opus for the implementer", "run the arena on three different models", "everything on the session model from here". That instruction wins from the next launch on. Update the role's entry on the `models:` line, log one row saying what changed and why, and keep going. A launch already running is not restarted. Nothing in the plugin checks a launch's model against the roster.

## Keep the arena diverse

Shipped defaults put `grok-4.7-high` on `arena-a` and `arena-c`, and `composer-2.5` on `arena-b`. If you override the contestants, keep them different.

The arena is a cook-off: three agents plan the same complex task in parallel, then `supercook-plan-judge` merges or picks. Three contestants on one model still give three independent attempts, but the value comes from genuinely different reasoning. Three families disagree in useful ways; three runs of one model mostly agree with themselves.

Setting `arena-a` to `inherit` is fine as long as your session model differs from `arena-b` and `arena-c`: it becomes the third family.
