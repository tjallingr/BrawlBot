import json
import re
from pathlib import Path

from rapidfuzz import fuzz

MATCH_THRESHOLD = 85


def normalize_name(name: str) -> str:
    name = re.sub(r"[^a-z0-9\s]", "", name.lower())
    return re.sub(r"\s+", " ", name).strip()


def load_overrides(path: Path) -> dict[str, str]:
    """A {normalized_name: fighter_ufcstats_id} escape hatch for names the
    fuzzy matcher can't resolve on its own (nicknames, transliterations)."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def best_fighter_match(name: str, candidates: dict[str, int], overrides: dict[str, int] | None = None) -> int | None:
    """candidates: {normalized_name: fighter_id}. Returns the best-matching
    fighter_id above MATCH_THRESHOLD, or None if nothing matches well enough."""
    normalized = normalize_name(name)
    if overrides and normalized in overrides:
        return overrides[normalized]
    if normalized in candidates:
        return candidates[normalized]

    scored = ((fuzz.ratio(normalized, candidate), fighter_id) for candidate, fighter_id in candidates.items())
    best_score, best_id = max(scored, default=(0, None))
    return best_id if best_score >= MATCH_THRESHOLD else None
