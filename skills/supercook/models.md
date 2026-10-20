# Model preferences

Every role below ships with a model already set. A role whose model your session does not offer falls back to `inherit`, which means it uses whatever model is driving the session, so the defaults never block a run.

## Where to edit

Two files can define the roster, and the parent reads both:

| File | Purpose |
|---|---|
| `~/.supercook/models.md` | Your choices. Applies to every repo. Wins wherever it names a role. |
| this file | The shipped default. A model for every role. |

**Edit the home file, not this one**, unless you cloned the repo and symlinked it into `~/.cursor/plugins/local/`. A marketplace install lives in a commit-pinned cache directory that the next plugin update replaces with a fresh one, so an edit made there is stranded the moment a new version lands. The home file is outside all of that.

It does not exist until you create it:

```bash
mkdir -p ~/.supercook
curl -fsSL https://raw.githubusercontent.com/hsaab/supercook/main/skills/supercook/models.md -o ~/.supercook/models.md
```

Then change the roles you want and delete the lines you do not. Any role the home file does not name falls through to this file, so a home file naming two roles changes exactly those two. Write `inherit` on a role to put it back on the session model.

Do not confuse `~/.supercook/` with the `.supercook/` folder inside a repo. The home one holds your model choices. The repo one holds run artifacts for that checkout, and nothing reads model preferences from it.

## The roster

```
standard:     claude-opus-5-5-high   # assessor, planner, test-designer, verifier
arena-a:      claude-fable-5-1-thinking-high
arena-b:      gpt-5.6-sol-max
arena-c:      claude-opus-5-5-high
plan-judge:   claude-opus-5-5-high
plan-optimizer: claude-opus-5-5-high
implementer:  grok-4.7-xhigh
explorer:     grok-4.7-xhigh
reviewer:     claude-opus-5-5-high   # bugbot, security-review, both thermo reviewers on the review track
review-implementer: cursor-grok-4.7-xhigh   # finding fixes on the review track
```

The two review-track roles are independent of the rest, like every role here: `reviewer` covers the four external reviewer launches on the review track, `review-implementer` covers the finding-fix launches there, and leaving either on `inherit` does not fall through to `implementer` or `standard`.

Every slug above was checked against a real model list rather than guessed. That matters here more than it looks: an unresolvable slug costs you a silent fallback, so shipping a plausible-looking slug that does not exist would undercut the point.

## How a role becomes a model

A slug written inside an agent file is not reliable. The model only takes effect when the parent passes it on the launch call, so the parent owns resolution:

1. **Read both files once**, at intake: `~/.supercook/models.md` first, then this one. A missing home file is the normal case, not an error, and never worth a word to the user.
2. **Merge per role, not per file.** A role named in the home file takes that value. Every other role falls back to this file. A home file that sets only `arena-b` and `arena-c` changes exactly those two.
3. **Validate each slug** against the models the launch tool actually offers in this session. `inherit` needs no check.
4. **Valid slug**: pass it on every launch for that role.
5. **Anything else** (typo, unavailable on this plan, renamed): inherit the parent model, log one ledger row naming the role and the rejected slug, and keep going. Never guess at a "nearest" model. A wrong guess is worse than inheriting, and no dependable resolver exists.
6. **Never block a run on a model name.**

The shipped slugs are defaults, not requirements. A plan that does not carry one loses that role to the session model and gains a ledger row, nothing more.

## Keep the arena diverse

The shipped arena already puts three different models on the three contestants. If you override any of them, keep them different.

The arena is a cook-off: three agents plan the same complex task in parallel, then `supercook-plan-judge` merges or picks. Three contestants on one model still give three independent attempts, but the value comes from genuinely different reasoning. Three families disagree in useful ways; three runs of one model mostly agree with themselves.

Setting `arena-a` to `inherit` is fine as long as your session model differs from `arena-b` and `arena-c`: it becomes the third family.
