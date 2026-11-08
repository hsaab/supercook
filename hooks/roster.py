"""Parse model roster files and ledger model headers (stdlib only)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROSTER_KEYS = frozenset(
    {
        "standard",
        "arena-a",
        "arena-b",
        "arena-c",
        "plan-judge",
        "plan-optimizer",
        "implementer",
        "explorer",
        "reviewer",
        "review-implementer",
    }
)

_ROSTER_SECTION = re.compile(r"^## The roster\s*$", re.MULTILINE)
_ROSTER_FENCE = re.compile(r"^```\n(.*?\n)^```", re.MULTILINE | re.DOTALL)

_LEDGER_FALLBACK = re.compile(
    r"^([a-zA-Z0-9_-]+)\s+inherit\s+\(unavailable\s+([^)]+)\)\s*$"
)
_LEDGER_PLAIN = re.compile(r"^([a-zA-Z0-9_-]+)\s+(\S+)\s*$")


@dataclass(frozen=True)
class LedgerModel:
    slug: str
    rejected_slug: str | None = None


def parse_roster(text: str) -> dict[str, str]:
    """Return role-to-slug entries from the fenced block under ## The roster."""
    section = _ROSTER_SECTION.search(text)
    if section is None:
        return {}

    after = text[section.end() :]
    fence = _ROSTER_FENCE.search(after)
    if fence is None:
        return {}

    result: dict[str, str] = {}
    for raw_line in fence.group(1).splitlines():
        parsed = _parse_roster_line(raw_line)
        if parsed is not None:
            role, slug = parsed
            result[role] = slug
    return result


def _parse_roster_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or ":" not in stripped:
        return None

    role, _, rest = stripped.partition(":")
    role = role.strip()
    if not role:
        return None

    hash_at = rest.find("#")
    if hash_at >= 0:
        rest = rest[:hash_at]
    slug = rest.strip()
    if not slug:
        return None

    return role, slug


def load_roster(
    repo_path: Path | None,
    home_path: Path,
    shipped_path: Path,
) -> dict[str, str]:
    """Merge per-role roster: repository override, then home, then shipped."""
    merged: dict[str, str] = {}

    if shipped_path.is_file():
        merged.update(parse_roster(shipped_path.read_text(encoding="utf-8")))

    if home_path.is_file():
        merged.update(parse_roster(home_path.read_text(encoding="utf-8")))

    if repo_path is not None and repo_path.is_file():
        merged.update(parse_roster(repo_path.read_text(encoding="utf-8")))

    return merged


def parse_ledger_models(text: str) -> dict[str, LedgerModel]:
    """Parse the ledger models: header line into per-role entries."""
    models_line: str | None = None
    for line in text.splitlines():
        if line.startswith("models:"):
            models_line = line
            break

    if models_line is None:
        return {}

    body = models_line.removeprefix("models:").strip()
    result: dict[str, LedgerModel] = {}

    for segment in body.split("|"):
        piece = segment.strip()
        if not piece:
            continue
        entry = _parse_ledger_segment(piece)
        if entry is not None:
            role, model = entry
            if role in ROSTER_KEYS:
                result[role] = model

    return result


def _parse_ledger_segment(segment: str) -> tuple[str, LedgerModel] | None:
    fallback = _LEDGER_FALLBACK.match(segment)
    if fallback is not None:
        role = fallback.group(1)
        rejected = fallback.group(2).strip()
        if rejected:
            return role, LedgerModel(slug="inherit", rejected_slug=rejected)
        return role, LedgerModel(slug="inherit", rejected_slug=None)

    plain = _LEDGER_PLAIN.match(segment)
    if plain is not None:
        role = plain.group(1)
        slug = plain.group(2)
        return role, LedgerModel(slug=slug, rejected_slug=None)

    return None
