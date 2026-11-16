---
name: setup-supercook
description: Check the supercook model roster against the models this session can launch, fix names that do not exist, and write the always-applied delegation rule. Use for /setup-supercook, "check supercook models", or after a launch rejected a model.
disable-model-invocation: true
---

# Setup supercook

Validate the roster, then write one rule. Re-running is safe.

## Steps

### 1. Resolve the roster

Resolve every role three times, once per [roster choice](../supercook/models.md#choosing-a-roster): `roster:repo`, `roster:machine`, and `roster:supercook`. Note the file each slug came from. `inherit` is always valid.

### 2. Detect launchable models

List the model slugs you can pass to `Task` in this session. If you cannot detect any, ask the user to paste the slugs they can use. Never write a slug you have not confirmed.

### 3. Validate

Compare every slug any of the three resolutions picked with the detected set. For each miss, name the role and the slug, offer the closest detected slug of the same family (highest effort at or below the original), and ask: use it, pick another, or `inherit`. Never substitute silently. Keep `arena-a`, `arena-b`, and `arena-c` on different families when you can.

### 4. Write the fixes

Write each fix to the file its slug came from, changing only that role's line and keeping the rest of the file, with two exceptions. A slug from the shipped `skills/supercook/models.md` is never edited there: its fix goes to `~/.supercook/models.md`, created if needed, and also to `<workspace-root>/.supercook/models.md` when that file exists and does not name the role, since it is the only override a cloud run sees. A slug from a `<plugin-root>/.supercook/models.md` outside this workspace is never edited there either: name the role and slug and say the fix belongs in the supercook repo's committed `.supercook/models.md`.

### 5. Write the delegation rule

Overwrite `<workspace-root>/.cursor/rules/supercook-delegation.mdc` with exactly this. Project rules are the documented route; a file under `~/.cursor/rules/` is not read.

```
---
description: Supercook delegation
alwaysApply: true
---
When `.supercook/active-run` names a ledger with an open `supercook-<role>` step, launch that worker with the spawn tool instead of doing the step yourself.
```

Keep it to that one sentence. The rule does nothing in a repo with no live supercook run. Commit it if you want Cloud Agents and other clones to get it.

### 6. Report

Say which roles changed and that the rule applies to new chats in this repo.
