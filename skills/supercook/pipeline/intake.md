# Phase 0: intake

Four steps, in this order. The order is not cosmetic: doing them out of sequence is how a ledger ends up in a directory the run abandons.

1. [Probe capabilities](#1-probe-capabilities)
2. [Decide the working tree](#2-decide-the-working-tree)
3. [Fix run identity](#3-fix-run-identity)
4. [Seed the ledger](#4-seed-the-ledger)

## 1. Probe capabilities

The rest of the workflow assumes git, a remote host, worktrees, and a test suite. UI work also needs a way to render the real route. Check rather than assume, and record what you find. Every missing capability has a degraded path, listed at the bottom of this file.

```bash
git rev-parse --is-inside-work-tree 2>/dev/null          # git at all?
git remote get-url origin 2>/dev/null                    # a remote?
gh auth status 2>&1 | head -3                            # GitHub, authenticated?
git worktree list 2>/dev/null                             # worktrees usable?
gt --version 2>/dev/null                                  # Graphite CLI present?
test -f "$(git rev-parse --git-path .graphite_repo_config 2>/dev/null)"  # gt init done?
gt auth 2>&1 | head -1                                    # Graphite authed? "No auth token set" means no
```

Also determine, without a separate agent launch:

- **The test command.** Look at the `scripts` block, the CI config, or a test runner config file. Do not guess from the language.
- **UI evidence in the task.** Record whether the request changes a rendered surface and whether it supplies a Figma URL, screenshot, attachment, or layout spec. Read [ui.md](ui.md) immediately when either fact is true.
- **The render check.** Note an available browser or computer-use tool, or an existing browser or end-to-end command in the repo. Record `none` when the route cannot be rendered yet. Recon refines the start command, route, state, and viewports. A trivial UI run that skips recon must do a minimal route, start-command, and representative-state lookup before verify.
- **Whether the supercook agents are installed.** If they are not, every role runs inline from its agent file body. See the fallback section in [../agents.md](../agents.md).
- **The model roster.** Read `~/.supercook/models.md` if it exists, then [../models.md](../models.md), and merge per role with the home file winning. A missing home file is the normal case: fall through to the shipped defaults without comment. Then check each uncommented slug against the models the launch tool offers in this session. A slug that is not available means inherit and log.
- **Stacking path.** Prefer Graphite when all three hold: `gt` is installed, the repo has been `gt init`-ed (`.graphite_repo_config` exists under the git dir), and Graphite is authenticated (`gt auth` does **not** print `No auth token set`). Otherwise use the manual stack lifecycle in [delivery.md](delivery.md#the-stack-lifecycle). Presence of `gt` alone is not enough: an unauthenticated CLI must record `stacking manual`.

Write one capability line to the ledger header:

```
capabilities: git yes | host github (gh authed) | worktrees yes | tests `pnpm vitest run` | PRs yes | stacking gt
ui-change: yes | ui-source: figma <canonical URL> | render-check: browser
```

`ui-change` and `ui-source` are independent. A UI change often has no supplied
design, and a design attached to an investigation does not authorize a UI change.

Use `stacking gt` when Graphite is usable, or `stacking manual` when it is not. Delivery and merge read that field and do not re-run the full probe. **Exception:** if a later `gt` command fails specifically because auth is missing or expired, rewrite the ledger capability to `stacking manual`, log the change, and continue on the manual path. Do not stay stuck on a sticky wrong mode.

**Cold merge exception.** On the merge track, `stacking gt` is only usable when the target PR's branch is already tracked by Graphite (it appears in `gt log` / `gt log short`). PRs opened with plain `git`/`gh` and never `gt track`-ed stay on the manual path for this run, even if the repo is otherwise Graphite-ready. Optionally `gt track --force` the chain first if the parent bases are clear; if tracking would guess wrong, keep `stacking manual` for the walk.

## 2. Decide the working tree

Do this before creating any file, so the ledger is born inside the tree the run will actually use.

```mermaid
flowchart TD
    start["Check current branch state"] --> clean{"Tree clean and on a sensible base?"}
    clean -->|yes| useCurrent["Work on the current branch"]
    clean -->|no| wt{"Worktrees available?"}
    wt -->|yes| newWt["Create a worktree off the default branch"]
    wt -->|no| tell["Say so, require a clean tree, work in place"]
```

Unrelated uncommitted or unpushed work is the case worktrees exist for. Do not stash someone's work and do not commit it into your run.

**The merge track skips this decision.** The PR's branch already exists, so there is nothing to create: check it out with `gh pr checkout <n>` and work there. No worktree and no new branch. See [../playbooks/merge.md](../playbooks/merge.md).

**Merge track plus Graphite.** Still check out the PR branch in place. Before `gt sync` / `gt submit` / `gt merge`, run `git worktree list` and confirm no other worktree has a stack sibling checked out. Graphite skips those branches, so a sibling parked in another worktree would be left stale. Free that checkout, or fall back to the manual restack for the affected children.

```bash
git worktree add ../<repo>-<slug> -b supercook/<slug> origin/<default-branch>
```

Creating a worktree is a reversible write, so it may need host approval. Ask once with the reason, log the answer, and continue. Never assume it.

**When stacking with Graphite**, run `gt sync`, `gt restack`, and `gt submit` from this run's working tree (the worktree when one exists, otherwise the checkout in use). From gt 1.8.4 onward those commands skip non-trunk branches that are checked out in another worktree, so stack maintenance done from the wrong tree silently leaves children stale.

## 3. Fix run identity

Resume depends entirely on this, so write it down before anything else happens.

- **run-id**: `<YYYY-MM-DD>-<slug>-<4 random chars>`. The random suffix is what keeps two runs on the same task apart.
- **repo**: the remote URL when one exists, else the output of `git rev-parse --show-toplevel`.
- **branch** and **worktree path**.
- **done**: the checkable predicate that ends this run. Write it as something you could test, not as an aspiration.

## 4. Seed the ledger

**Skip this step entirely on the investigation track**, and on any request that is explicitly read-only. Those runs keep the record in the todo list instead, which satisfies the same purpose without writing to someone's repo during a read-only ask. See [../playbooks/investigation.md](../playbooks/investigation.md). Steps 1 through 3 still run, minus the worktree.

Otherwise: create `.supercook/<run-id>/` in the chosen tree, then write `ledger.md` with the header, every phase as an unchecked row, and the routed playbook's steps copied in verbatim. Format and lifecycle rules live in [ledger.md](ledger.md).

**The merge track does not get the investigation exception.** It changes the repo and it can span sessions while checks run, so it needs the record more than most runs, not less. Seed the ledger, with the target PR number in the header.

**On `implement-plan`, pin the supplied plan next.** Once the run folder exists, copy the resolved plan source verbatim to `user-plan.md` in that folder and echo the plan title. Later phases read that file, not chat scrollback. See [../playbooks/implement-plan.md](../playbooks/implement-plan.md).

Keep the run folder out of git without touching `.gitignore`:

```bash
EXCLUDE=$(git rev-parse --git-path info/exclude)
grep -qxF '.supercook/' "$EXCLUDE" 2>/dev/null || printf '\n.supercook/\n' >> "$EXCLUDE"
```

Use `git rev-parse --git-path`, never a literal `.git/info/exclude`. A linked worktree has a `.git` **file**, not a directory, so the literal path does not exist there and a plain append would create a stray file that excludes nothing.

Three things about that write. The `grep -qxF` guard is what makes it idempotent, since this runs once per run and the entry only needs to exist once. The leading newline in `printf` protects against an exclude file that does not end in one, which would otherwise glue the entry onto the previous line and break both. And the path resolves to the **shared** exclude file, so the entry covers every worktree of the repo and outlives this run. That last part is acceptable, since it is one line in a file git never commits, but it should not be a surprise.

Skip the write entirely when the probe says this is not a git repo.

Finally, mirror the phase rows into the todo list so progress is visible live.

## Degraded paths

Announce the degradation in one line, log it, and continue. Never fail the run over a missing capability.

| Missing | What changes |
|---|---|
| git | No worktree, no branch, no PR. Work in place, keep the run folder in the system temp dir, deliver a summary plus the diff. |
| GitHub, or `gh` not authenticated | Phases 0 through 7 run unchanged. Delivery stops at a pushed branch or a local commit series, with the PR body written into the run folder to paste wherever it is needed. |
| Worktree support | Say so, require a clean tree, work on the current branch. |
| Graphite CLI, `gt` not authenticated, repo not `gt init`-ed, or non-GitHub host | Record `stacking manual`. Delivery and merge use the manual stack lifecycle in [delivery.md](delivery.md#the-stack-lifecycle) and [merge.md](merge.md#stacked-prs). Everything else is unchanged. |
| A runnable test suite | Test-first becomes verification-first. The test designer returns an executable recipe; the parent writes it in the run folder and records its path in `plan.md`, or the ledger on open-pr, and the verifier runs it. The journey thinking survives; only the assertion mechanism changes. |
| A readable supplied UI source | Ask once for a screenshot, a written layout spec, or authorization to proceed without it. Record the answer before planning. Never invent the source's contents. |
| A renderer for a changed route | Write a fully specified manual smoke row with the route, state, viewports, and checks. It is sanctioned-blocked until the user confirms it or accepts delivery with the missing visual evidence named. |
| Write access | Investigation track only, since nothing can ship. Same no-file behavior as that track. |
| The supercook agents | Roles run inline from the agent file bodies. |
| A valid model slug | Inherit, log once, continue. |
| `~/.supercook/models.md` | Use the shipped roster in `../models.md`. This is the default state, so say nothing and log nothing. |
| A PR template, or one that is mandatory | The three PR body sections become the minimum content and get fitted into the template's fields rather than replacing them. Check for `.github/pull_request_template.md` during the probe. |
