# Supercook subagent launch (parent agent)

Read this before every `CallDynamicTool` with `toolName: Task` or a `CreateAgent` spawn.

**Scope.** These shapes apply only to parents whose own tool list has `CallDynamicTool` (with a `cursor` `Task` tool) or `CreateAgent`, such as Grok Bot, a Project coordinator, or a Cloud Agent that reaches `Task` through its dynamic tool catalog. A session with a different spawn tool launches the named `supercook-<role>` worker through that tool's own listed schema; a session with no spawn tool runs each role inline from its agent file. Both paths are in [skills/supercook/agents.md](../../skills/supercook/agents.md#spawn-paths-when-typed-agents-are-missing). Do not build these envelopes for a tool you cannot see.

## Wire format

| Field | Task (`CallDynamicTool`) | CreateAgent / coordinator `Subagent` |
| --- | --- | --- |
| `description` (required) | only under `arguments` | top level |
| `subagent_type` (required) | only under `arguments` | top level |
| `prompt` (required) | only under `arguments` | top level |
| `model` | only under `arguments` | top level |
| `environment` (`local` or `cloud`, default `local`) | only under `arguments` | top level |
| `cloud_base_branch` (only with `environment: "cloud"`; the branch must already be pushed) | only under `arguments` | top level |
| `run_in_background`, `interrupt` | only under `arguments` | top level |
| `resume`, `file_attachments` | only under `arguments` | top level |

Task envelope: `{"namespace": "cursor", "toolName": "Task", "arguments": { ... }}`. For Task, every launch field goes only under `arguments`. CreateAgent and Subagent: same launch field names at the top level, never under `arguments`.

Do not set `model` together with `resume`. Omit `model` when the roster resolves that role to `inherit`.
Pass `model` as the slug resolved from the three-tier roster files at intake: repository `.supercook/models.md`, then `~/.supercook/models.md`, then the shipped roster. Intake records that slug on the run ledger's `models:` line for resume only; the roster hook compares `model` against the merged roster files, not the ledger, except when `model` is omitted and the ledger has `inherit (unavailable …)`.
An entry `<role> inherit (unavailable <slug>)` means omit `model`.
The model values in the examples below come from one run's roster and differ per machine; a cloud VM without your home roster resolves to the shipped defaults.

## Platform error (PR #148)

Invalid arguments: `prompt — expected string, received undefined` when Task fields sit beside `namespace` / `toolName` instead of inside `arguments`, or when broken JSON escaping in a long inline prompt makes `prompt` undefined at parse time. The rejected PR #148 shape is below.

## Local vs cloud

- `environment: "local"` (default) runs the subagent on the same machine and checkout as the parent, whether the parent is in the IDE or is itself a cloud agent, so it can read the parent's files including `.supercook/`.
- Prefer `local` for every supercook role, including when the parent is a Cloud Agent: the run folder lives only on the parent's checkout.
- `environment: "cloud"` runs the subagent on its own VM. With `cloud_base_branch` set, it starts from that pushed branch; without `cloud_base_branch`, a cloud subagent starts from the parent's current branch on the remote, so push that branch before launch.
- Set `cloud_base_branch` only with `environment: "cloud"`. Push that branch to the remote before launch; the validator does not check the remote.
- A cloud subagent cannot read `.supercook/` (git-excluded on the parent). Put run context, slice scope, and the full prompt inline in `arguments.prompt`; do not tell it to open a `.supercook/` path.
- Every supercook prompt carries `supercook-role:` and `supercook-run:`, local and cloud; the roster hook reads them on the parent side before launch. A cloud subagent must not try to open that path.

## Long prompts

Write `.supercook/prompts/<phase>-<role>.md`, then build with `task --prompt-file` so the parent inlines file content into `arguments.prompt`. Inline prompt text, never a filesystem path in JSON.

## Valid examples

<!-- validate: task-valid -->
```json
{"namespace": "cursor", "toolName": "Task", "arguments": {"description": "Verify slice", "subagent_type": "supercook-verifier", "prompt": "supercook-role: standard\nsupercook-run: .supercook/2026-11-07-subagent-launch-k3q9\n", "model": "claude-opus-5-5-high"}}
```

<!-- validate: task-valid -->
```json
{"namespace": "cursor", "toolName": "Task", "arguments": {"description": "Cloud implement", "subagent_type": "supercook-implementer", "prompt": "supercook-role: implementer\nsupercook-run: .supercook/2026-11-07-subagent-launch-k3q9\nfull inline brief here", "model": "composer-2.5", "environment": "cloud", "cloud_base_branch": "supercook/x"}}
```

<!-- validate: create-agent-valid -->
```json
{"description": "Plan slice", "subagent_type": "supercook-planner", "prompt": "supercook-role: standard\nsupercook-run: .supercook/2026-11-07-subagent-launch-k3q9\nPlan only.\n", "model": "claude-opus-5-5-high"}
```

## Invalid example (PR #148)

<!-- validate: task-invalid -->
```json
{"namespace": "cursor", "toolName": "Task", "description": "Implement", "subagent_type": "supercook-implementer", "prompt": "..."}
```

## Pre-flight

Run from any cwd. Replace `<repo>` with the absolute repo root. Copy the printed JSON into `CallDynamicTool` unchanged (do not retype).

Build a local Task launch from a prompt file:

<!-- run: exit=0 -->
```bash
mkdir -p .supercook/prompts
printf 'supercook-role: standard\nsupercook-run: .supercook/2026-11-07-subagent-launch-k3q9\n' > .supercook/prompts/7-verifier.md
python3 <repo>/scripts/validate_subagent_launch.py task \
  --description 'Verify slice' \
  --subagent-type supercook-verifier \
  --prompt-file .supercook/prompts/7-verifier.md \
  --model claude-opus-5-5-high
```

Build a cloud Task launch (branch already pushed):

<!-- run: exit=0 -->
```bash
mkdir -p .supercook/prompts
printf 'supercook-role: implementer\nsupercook-run: .supercook/2026-11-07-subagent-launch-k3q9\n' > .supercook/prompts/6-implementer.md
python3 <repo>/scripts/validate_subagent_launch.py task \
  --description 'Cloud implement' \
  --subagent-type supercook-implementer \
  --prompt-file .supercook/prompts/6-implementer.md \
  --model composer-2.5 \
  --environment cloud \
  --cloud-base-branch supercook/x
```

Validate CreateAgent stdin:

<!-- run: exit=0 -->
```bash
printf '%s' '{"description":"Plan","subagent_type":"supercook-planner","prompt":"supercook-role: standard\nsupercook-run: .supercook/2026-11-07-subagent-launch-k3q9\nhi\n","model":"claude-opus-5-5-high"}' \
  | python3 <repo>/scripts/validate_subagent_launch.py create-agent
```

Reject PR #148 shape:

<!-- run: exit=1 -->
```bash
printf '%s' '{"namespace":"cursor","toolName":"Task","description":"Implement","subagent_type":"supercook-implementer","prompt":"..."}' \
  | python3 <repo>/scripts/validate_subagent_launch.py task
```

Pipe a saved envelope through `task` to double-check before launch:

<!-- run: exit=0 -->
```bash
printf '%s' '{"namespace":"cursor","toolName":"Task","arguments":{"description":"Verify","subagent_type":"supercook-verifier","prompt":"supercook-role: standard\nsupercook-run: .supercook/2026-11-07-subagent-launch-k3q9\nok","model":"claude-opus-5-5-high"}}' \
  | python3 <repo>/scripts/validate_subagent_launch.py task
```

## On failure

A validator rejection means fix and re-run, never run the role inline. A roster hook model denial is fix-and-relaunch (correct slug or omit for inherit), not parent inline: fix the `model` slug and relaunch, or launch `generalPurpose` with the agent prompt per `skills/supercook/agents.md`. Never parent-implement for `implementer` or `review-implementer` instead of launching the subagent. Limit `degraded: parent inline` to non-roster platform or tool errors after retry on an already validated launch, or to a session with no spawn tool at all (`spawn: none`); log the exact error or `spawn none`, then run the role yourself from its agent file. Never silently parent-implement instead of launching the subagent.
