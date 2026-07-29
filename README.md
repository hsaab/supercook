# Supercook

A development workflow you invoke with one command, that scales its own process to the risk of the task.

`/supercook fix the webhook 500s` gets a small, focused fix. `/supercook add rate limiting to the public API` gets architecture alignment, a multi-model planning arena, tests written before implementation, an independent audit, and three reviewable PRs. Same command.

## Why this exists

Orchestrator skills are becoming one of the more useful things you can build for an agent, for three reasons.

They unlock long-running work. An agent with an external ledger and a defined pipeline can survive context resets and keep going, which is what goal-oriented and cloud agent runs actually require.

They make sharing practice trivial. Packaged as a plugin, your team's way of working installs in one step instead of living in someone's head or in a wiki nobody reads.

They give repeatability. For work that recurs (bugs, features, refactors, opening PRs), a golden path means good results every time instead of results that depend on how the prompt was phrased.

## When to use it, and what to expect

Use it for anything development related: bugs, features, investigations, refactors, tests, performance work, and turning existing changes into a PR.

One command does not mean one heavyweight process. Supercook classifies the task first, then scales ceremony to the risk:

- **Trivial.** Work directly, verify, done. No exploration phase, no arena, no test ceremony. A copy fix stays a copy fix. The one thing that can still fire here is architecture alignment, because a two line change can still alter an interface other people depend on.
- **Standard.** Targeted exploration, a short plan, tests for the real user journeys, surgical implementation, an independent verification pass, and usually one reviewable PR. Most work lands here.
- **Complex.** Everything above plus a broad codebase map, architecture alignment when the approach needs sign-off, three models planning in parallel with a judge picking or merging, tests committed per slice, verification before every PR, and multiple coherent PRs.

Tracks skip what does not apply. An investigation stays read-only and produces an answer rather than a PR, and it writes nothing to your repo at all. `open-pr` skips planning and implementation, but still verifies the diff and runs the suite before opening. A refactor starts by pinning current behavior with tests.

> Use Supercook for anything development related. Tell it the outcome you want, and it decides how much process the work deserves. Small tasks stay small. Normal changes get a focused plan, implementation, verification, and usually one reviewable PR. Large or risky changes add architecture alignment, deeper exploration, test-first development, independent review, and multiple coherent PRs. You can expect visible progress in the ledger, no silently skipped work, and a short outcome-focused handoff.

## The flow

```mermaid
flowchart LR
    task["Task in"] --> assess["Assess: how much process?"]
    assess --> plan["Plan: slices sized for review"]
    plan --> tests["Tests first, from user journeys"]
    tests --> build["Implement in surgical chunks"]
    build --> verify["Verify with fresh eyes"]
    verify --> pr["PR out, in plain language"]
```

## Key principles, and why they work

**Explanations name the file, the change, and the real consequence.** Written like a sharp junior engineer who just read the code, not like a changelog. "We changed `handleWebhook` in `src/api/webhook.ts` because it still referenced a `retryCount` variable the queue rewrite deleted, so any real webhook would have thrown and taken the server down." Not "improved error handling". This is the principle that makes the rest checkable, so it sits at the top of the skill. An opinionated style choice, not a research finding.

**Subagents with clean context and terse return contracts.** Each role gets an objective, inputs, an effort budget, boundaries, and a fixed output shape, so results stay small and the orchestrator's context stays usable. ([Anthropic on multi-agent systems](https://www.anthropic.com/engineering/multi-agent-research-system))

**The ledger as external memory.** Every phase and every skip is written to a file, so context resets and new sessions resume from the record rather than from a guess. ([Anthropic on context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), the structured note-taking pattern)

**Ceremony scales with complexity.** Single agent first, the arena only when the task pays for it. ([Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents), [OpenAI's practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf))

**The arena plus a judge** is parallelization combined with the evaluator-optimizer pattern: three independent plans, then one agent picking or merging with stated provenance. ([Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents))

**Effort budgets and boundaries in every delegation.** Agents over-invest and under-invest without an explicit scale, which Anthropic reports as their most common multi-agent failure mode. ([Anthropic on multi-agent systems](https://www.anthropic.com/engineering/multi-agent-research-system))

**Progressive disclosure.** `SKILL.md` stays lean and links one level deep, so a phase guide only enters context when that phase runs. ([Anthropic on Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills))

**Action-risk tiers.** Read-only actions run, reversible writes run and get logged, irreversible ones ask every time. ([OpenAI's practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf))

**Test-driven, with the suite protected.** Failing tests are committed first, the implementing agent is forbidden from touching them, and the orchestrator restores any test file that gets modified anyway. That last part matters: an instruction alone does not stop an agent bending a test until it passes. ([Cursor's agent best practices](https://cursor.com/blog/agent-best-practices))

**Boundaries are enforced, not requested.** Every rule that matters has a check that runs after the agent returns. Prompts express intent; the checks are what make it a control.

**Opinionated style choices**, with no research behind them and no pretense otherwise: surgical diffs, PRs under about 500 reviewable lines, keep going wherever host permissions allow, and no em dashes anywhere.

## Install

```bash
git clone https://github.com/hsaab/supercook.git ~/Apps/supercook
ln -s ~/Apps/supercook ~/.cursor/plugins/local/supercook
```

Reload the window, then confirm you see two skills (`supercook`, `merge-pr`) and eight agents (`supercook-assessor`, `-explorer`, `-planner`, `-arena-runner`, `-plan-judge`, `-test-designer`, `-implementer`, `-verifier`).

If the loader rejects the symlink, clone directly into `~/.cursor/plugins/local/supercook` instead, and update with `git pull`.

One thing to know before the first run: without worktree support it works on your current branch, and in that case it needs a clean tree. It will say so rather than stashing anything.

This is a public repo with a manual install. It is not a Cursor Marketplace listing, which is a separate submission step.

## Bring your own models

Everything is configured in one file: [skills/supercook/models.md](skills/supercook/models.md).

Every role ships as `inherit`, meaning it uses whatever model is driving your session, with suggested slugs commented next to each role. Uncomment what you want. The orchestrator validates each slug at the start of a run and falls back to inherit with a note in the ledger if your plan does not carry it, so nothing breaks and nothing is guessed.

**The one edit worth making:** get three different model families into the arena. Three contestants on one model mostly agree with themselves, and the disagreement is the entire value of a cook-off. Setting `arena-b` and `arena-c` to two other families is enough, since `arena-a` left on `inherit` contributes whatever model is already driving your session.

## What it needs, and what happens without it

Happiest with git, GitHub plus an authenticated `gh`, worktree support, and a runnable test suite. It degrades rather than fails without them:

| Missing | What happens |
|---|---|
| GitHub or `gh` | Stops at a pushed branch, with the PR body written to the run folder |
| A test runner | Tests become an executable verification recipe the verifier runs |
| Worktrees | Works on the current branch, after saying so, and requires a clean tree |
| git | Works in place, delivers a summary and the diff |
| The plugin's agents | Roles run inline from the agent file bodies |

**One limit worth knowing.** Run artifacts live in `.supercook/` in your repo, untracked, excluded via git's local exclude file rather than your `.gitignore`. They survive new sessions in the same checkout. They do not travel to another machine or a cloud agent unless you deliberately commit the ledger.

## Usage

```
/supercook <what you want>
/supercook plan only <what you want>      # stop after the plan
/supercook no PR <what you want>          # implement and verify, do not open a PR
/supercook no commits <what you want>     # leave the changes uncommitted
/merge-pr                                  # drive a PR to merged
```

Playbooks, routed automatically from the assessment:

| Track | What it does differently |
|---|---|
| bugfix | Reproduces first, proves the root cause, lands a failing repro test before the fix |
| feature | Names the data shape before the logic, tests real journeys, full pipeline |
| investigation | Read-only, cited answer, no plan or tests or PR, and nothing written to your repo |
| refactor | Pins current behavior with characterization tests, reroutes if behavior changes |
| open-pr | No planning or implementation, but the diff is still verified, for work already in the tree |

## Layout

```
agents/                       eight discoverable subagents, all supercook- prefixed
skills/supercook/
  SKILL.md                    principles, pipeline, routing, autonomy
  models.md                   the one file for model choices
  agents.md                   launch contracts and the parent-side guards
  pipeline/                   eight guides for the nine phases, loaded when the phase runs
  playbooks/                  one per track
skills/merge-pr/SKILL.md      drive a PR to merged, including stacks
```

## License

MIT
