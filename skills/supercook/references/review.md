# Review sources and fan-out

## Reuse hosted Bugbot

Bugbot often already ran on the PR. When it did, its findings are the review; read them instead of paying for it twice. The thermo reviewers have no hosted form and always run locally. Security review has no confirmed hosted check name yet, so it is always `local`.

Resolve Bugbot to `hosted`, `local`, or `pending` against the PR's head:

```bash
HEAD_SHA=$(gh pr view <n> --json headRefOid --jq .headRefOid)
gh api --paginate "repos/{owner}/{repo}/commits/$HEAD_SHA/check-runs" \
  --jq '.check_runs[] | {name, app: .app.slug, status, conclusion, started_at, output}'
```

Only a check run named exactly `Cursor Bugbot` from the `cursor` app counts (`Cursor Bugbot Autofix` does not). With several runs on the head, the latest `started_at` wins. First matching row:

| Bugbot's run on the head | Source |
|---|---|
| completed, `success` or `neutral`, and `output.summary` says `completed review` | `hosted` |
| completed any other way (the app also reports `neutral` for a run that failed to start) | `local` |
| not completed yet, started under 30 minutes ago | `pending` |
| none, and the head was pushed under 10 minutes ago | `pending` |
| none, or still not completed after 30 minutes | `local` |

A pending reviewer never holds the fan-out: launch the local batch now and keep resolving it. If it lands on `local`, launch it then and ignore any hosted result that arrives later for this head. Hosted findings come from the check run's `output`, plus the `cursor` author's review bodies on the head (`gh pr view <n> --json reviews`) and its unresolved, non-outdated review threads whose first comment's `originalCommit` is the head (GraphQL `reviewThreads`; REST lacks both flags). Record each source and the head SHA it was judged on.

## The fan-out

Check out the PR branch first, because the reviewers read the working tree. Launch both thermo reviewers plus every `local` reviewer in one parallel batch, each with the `reviewer` model; none depends on another, so launching them one at a time only multiplies wall time.

- `bugbot` and `security-review` compute the diff themselves. Use exactly this prompt; `Base Branch` is what keeps a stacked slice from being blamed for its parents' code:

  ```
  Full Repository Path: <absolute path to this run's working tree>
  Diff: branch changes
  Base Branch: <this PR's base branch>
  ```

- `thermo-nuclear-review-subagent` and `thermo-nuclear-code-quality-review-subagent` get the diff in the prompt (`git diff <base>...HEAD` plus the changed files they need), asking for prioritized findings with file references and evidence.
- A reviewer not installed on this host is recorded as a gap in the ledger and the summary. Never fake one with a generic agent.

## Triage, fix, confirm

Dedupe across every reviewer (overlaps carry more weight), then triage each finding per [merge.md](merge.md#comment-triage). The in-scope list goes to one `supercook-implementer` launch on the `review-implementer` key, with each finding's file, claim, and surviving evidence; the scope is the union of files they name, and the PR's test command is the verification. Record each decline in the ledger and on the PR.

After the fixes are pushed, run one confirmation pass on only the reviewers whose findings were fixed, resolving sources again against the new head. Triage what it finds; at most one more implementer launch, and no third pass. Anything still open is reported on the PR, because reviewers can disagree with each other's fixes forever.

The CI wait covers CI and test checks. Review-bot checks are covered by the source decision and the confirmation pass, unless the repo marks one as required.
