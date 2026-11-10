"""Worker-return additional_context text (pure, no guard imports)."""

from __future__ import annotations


def worker_return_note(
    returned_worker: str,
    first_owed_worker: str | None,
) -> str:
    """Build postToolUse relaunch guidance from already-resolved facts."""
    lines = [
        f"{returned_worker} returned.",
        (
            "A thin or wrong return needs a fresh relaunch with the roster model "
            "on the launch tool, not a rebuilt answer in chat."
        ),
    ]
    if first_owed_worker:
        lines.append(f"Next open worker on the ledger is {first_owed_worker}.")
    else:
        lines.append(
            "No ledger resolved: on the investigation track stay read-only and "
            "do not write product code."
        )
    return "\n".join(lines)
