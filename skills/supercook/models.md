# Model preferences

Every role below ships with a model already set. A role whose model your session does not offer falls back to `inherit`, which means it uses whatever model is driving the session. The parent announces that fallback once at intake, records it in the ledger `models:` header, and never blocks the run.

## Where to edit

Three files can define the roster. The parent and the roster hook read all three and merge **per role**, highest tier wins:

| Precedence | File | Purpose |
|---|---|---|
| 1 (wins) | `<workspace-root>/.supercook/models.md` | Optional override for this checkout. Names a role here and only that role changes. |
| 2 | `~/.supercook/models.md` | Your choices outside any repo. Wins for any role the repository file does not name. |
| 3 | this file (`skills/supercook/models.md`) | Shipped default. A model for every role when neither override names it. |

**Edit the home file or the repository file, not this one**, unless you cloned the repo and symlinked it into `~/.cursor/plugins/local/`. A marketplace install lives in a commit-pinned cache directory that the next plugin update replaces with a fresh one, so an edit made there is stranded the moment a new version lands. The home and repository paths are outside all of that.

The home file does not exist until you create it:

```bash
mkdir -p ~/.supercook
curl -fsSL https://raw.githubusercontent.com/hsaab/supercook/main/skills/supercook/models.md -o ~/.supercook/models.md
```

The repository file is optional: create `<workspace-root>/.supercook/models.md` with the same fenced roster shape when this checkout should pin models for your session. That path lives under repo `.supercook/`, which is checkout-local and often git-excluded, so it is not automatically shared with other clones unless you commit or copy it on purpose.

Then change the roles you want and delete the lines you do not. Any role a higher file does not name falls through to the next tier, so a home file naming two roles changes exactly those two only when the repository file does not name those roles. Write `inherit` on a role to put it back on the session model.

Do not confuse `~/.supercook/` with the `.supercook/` folder inside a repo. The home one holds your personal model choices. The repo `.supercook/` folder holds run artifacts for that checkout **and** may hold an optional `models.md` override that wins over home and shipped for roles it names.

## The roster

```
standard:     claude-opus-5-5-high        # assessor, planner, test-designer, verifier; e.g. claude-opus-5-5-high
arena-a:      inherit                     # third arena family = session model; or pin e.g. claude-fable-5-1-thinking-max
arena-b:      gpt-5.6-sol-max             # e.g. gpt-5.6-sol-max
arena-c:      claude-opus-5-5-high        # e.g. claude-opus-5-5-high
plan-judge:   claude-opus-5-5-high        # e.g. claude-opus-5-5-high
plan-optimizer: claude-opus-5-5-high
implementer:  cursor-grok-4.6-high-fast   # e.g. cursor-grok-4.6-high-fast
explorer:     cursor-grok-4.6-high-fast   # e.g. cursor-grok-4.6-high-fast
reviewer:     claude-opus-5-5-high        # bugbot, security-review, both thermo reviewers on the review track
review-implementer: cursor-grok-4.6-high-fast   # finding fixes on the review track
```

The two review-track roles are independent of the rest, like every role here: `reviewer` covers the external reviewer launches on the review track (up to four per PR, fewer when hosted results are reused), `review-implementer` covers the finding-fix launches there, and leaving either on `inherit` does not fall through to `implementer` or `standard`.

Every slug above was checked against a real model list rather than guessed. An unresolvable slug still costs you a fallback to `inherit`, but intake tells you once and writes the ledger header so the roster hook can allow an omitted model for that role. Shipping a plausible-looking slug that does not exist undercuts that transparency.

## How a role becomes a model

A slug written inside an agent file is not reliable. The model only takes effect when the parent passes it on the launch call, so the parent owns resolution:

1. **Read all three roster files once, at intake**, merging per role: `<workspace-root>/.supercook/models.md`, then `~/.supercook/models.md`, then this file. A missing file at either override tier is the normal case, not an error, and never worth a word to the user.
2. **Merge per role, not per file.** For each roster key, the repository value wins over the system value, which wins over the shipped value. A repository file that sets only `arena-b` changes exactly `arena-b`.
3. **The roster is the user's explicit model request.** Pass the resolved slug verbatim on every launch. Never substitute a "latest", "nearest", or guessed alternative when the slug is valid in the roster.
4. **Validate each slug** against the models the launch tool actually offers in this session. `inherit` needs no check.
5. **Anything else** (typo, unavailable on this plan, renamed): treat the role as `inherit` for launches (omit the model field). Tell the user once at intake which roles fell back, and write the ledger header entry as `<role> inherit (unavailable <slug>)` (for example `arena-b inherit (unavailable gpt-5.6-sol-max)`). Log the rejection in the ledger body if useful. Never guess at a "nearest" model.
6. **Never block a run on a model name.**

The shipped slugs are defaults, not requirements. A plan that does not carry one loses that role to the session model after the one-time announcement and header entry.

### Ledger header vs roster hook

The ledger `models:` line and `enforce_roster` answer different questions. The three-tier roster files (repository, home, shipped) set the **expected slug** for each role on every launch. The hook merges those tiers the same way intake does and compares the launch's model field against that expectation.

The ledger header is the run's resume and audit record. **`models-resolved:`** is the map coordinators read for launch: every roster key to either a validated slug or plain `inherit`. **`models:`** carries the same resolution for the roster hook, using `<role> inherit (unavailable <slug>)` when intake announced a fallback. List every roster key on both lines. Positive entries document what intake resolved; they do not replace the file merge on a fresh launch unless you rely on them only for human context. Entries marked `inherit (unavailable ...)` on `models:` are what the hook consults when the model field is omitted: they allow an omitted model for that role only after intake announced the fallback. For roles with a positive slug on the header, the hook still resolves the expected slug from the three-tier files unless that inherit form appears for the role.

## Tags on every launch

Every supercook subagent launch must carry two line-anchored tags anywhere in `tool_input.prompt`:

- `supercook-role: <roster-key>`
- `supercook-run: <absolute or relative run folder path>`

The role tag is always a **roster key**, not the agent type name. `supercook-assessor`, `supercook-planner`, `supercook-test-designer`, and `supercook-verifier` all tag `supercook-role: standard`, matching the "Role in models.md" column in [agents.md](agents.md). Other agents tag their own key (`explorer`, `implementer`, `arena-a`, and so on). Review-track hosts use `reviewer` or `review-implementer`; see [playbooks/review.md](playbooks/review.md) for where those tags sit in fixed prompt shapes.

## Roster hook (deny only)

The plugin ships a **preToolUse** hook (`hooks/enforce_roster.py`, matchers `Subagent` and `Task`) that runs on subagent launches. It:

- Parses the first line-anchored `supercook-role:` and `supercook-run:` in the prompt.
- Resolves the expected slug with the same three-tier lookup (repository root from `workspace_roots` and the resolved run folder, then home, then shipped defaults next to the hook script).
- Reads `<run folder>/ledger.md` for a `models:` header line; entries like `<role> inherit (unavailable <slug>)` let an omitted model pass for that role only after intake announced the fallback.
- **Denies** when the passed model does not match the expected slug, when a `supercook-*` launch has no tags, when the role tag is not a roster key, or when a role rostered as `inherit` still receives a model. It does not rewrite launches.
- **Fails open:** script errors, bad stdin, or a failing hook command allow the launch to proceed so unrelated work is never blocked.

## Keep the arena diverse

The shipped arena already puts three different models on the three contestants. If you override any of them, keep them different.

The arena is a cook-off: three agents plan the same complex task in parallel, then `supercook-plan-judge` merges or picks. Three contestants on one model still give three independent attempts, but the value comes from genuinely different reasoning. Three families disagree in useful ways; three runs of one model mostly agree with themselves.

Setting `arena-a` to `inherit` is fine as long as your session model differs from `arena-b` and `arena-c`: it becomes the third family.
