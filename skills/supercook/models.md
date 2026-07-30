# Model preferences

Every role below ships as `inherit`, which means it uses whatever model is driving the session. The suggested slugs sit commented next to each role. Uncomment one to opt into it.

## Where to edit

Two files can define the roster, and the parent reads both:

| File | Purpose |
|---|---|
| `~/.supercook/models.md` | Your choices. Applies to every repo. Wins wherever it names a role. |
| this file | The shipped default. Every role `inherit`. |

**Edit the home file, not this one**, unless you cloned the repo and symlinked it into `~/.cursor/plugins/local/`. A marketplace install lives in a commit-pinned cache directory that the next plugin update replaces with a fresh one, so an edit made there is stranded the moment a new version lands. The home file is outside all of that.

It does not exist until you create it:

```bash
mkdir -p ~/.supercook
curl -fsSL https://raw.githubusercontent.com/hsaab/supercook/main/skills/supercook/models.md -o ~/.supercook/models.md
```

Then uncomment the roles you want. Roles you leave commented fall through to this file, so a home file naming two roles changes exactly those two.

Do not confuse `~/.supercook/` with the `.supercook/` folder inside a repo. The home one holds your model choices. The repo one holds run artifacts for that checkout, and nothing reads model preferences from it.

## The roster

```
standard:     inherit    # suggested: claude-fable-5-thinking-max   (assessor, planner, test-designer, verifier)
arena-a:      inherit    # suggested: claude-fable-5-thinking-max
arena-b:      inherit    # suggested: gpt-5.6-sol-max
arena-c:      inherit    # suggested: claude-opus-5-thinking-high
plan-judge:   inherit    # suggested: claude-opus-5-thinking-high
implementer:  inherit    # suggested: cursor-grok-4.5-high-fast
explorer:     inherit
```

Every suggested slug above was checked against a real model list rather than guessed. That matters here more than it looks: this file's entire argument is that an unresolvable slug costs you a silent fallback, so shipping a plausible-looking slug that does not exist would undercut the point.

## How a role becomes a model

A slug written inside an agent file is not reliable. The model only takes effect when the parent passes it on the launch call, so the parent owns resolution:

1. **Read both files once**, at intake: `~/.supercook/models.md` first, then this one. A missing home file is the normal case, not an error, and never worth a word to the user.
2. **Merge per role, not per file.** A role named by an uncommented line in the home file takes that value. Every other role falls back to this file. A home file that sets only `arena-b` and `arena-c` changes exactly those two.
3. **Validate each uncommented slug** against the models the launch tool actually offers in this session.
4. **Valid slug**: pass it on every launch for that role.
5. **Anything else** (typo, unavailable on this plan, renamed): inherit the parent model, log one ledger row naming the role and the rejected slug, and keep going. Never guess at a "nearest" model. A wrong guess is worse than inheriting, and no dependable resolver exists.
6. **Never block a run on a model name.**

Uncommenting a line is your explicit request for that override. That is why nothing ships uncommented: picking models on your behalf, from a list your plan may not even carry, is not a default worth having.

## The one edit worth making

Give the three arena roles three **different** model families, in `~/.supercook/models.md`.

The arena is a cook-off: three agents plan the same complex task in parallel, then `supercook-plan-judge` merges or picks. Three contestants on one inherited model still give three independent attempts, but the value comes from genuinely different reasoning. Three families disagree in useful ways; three runs of one model mostly agree with themselves.

So if you set one thing, make it the arena. Leaving `arena-a` on `inherit` is fine and even useful: your session model becomes the third family, alongside whatever you give `arena-b` and `arena-c`.
