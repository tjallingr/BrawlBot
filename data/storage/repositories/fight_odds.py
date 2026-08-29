from datetime import datetime, timezone

from data.storage.models import FightOdds
from data.storage.repositories.fights import get_fight_by_fighter_pair
from scrape.reconcile.name_match import best_fighter_match


def store_fight_odds(session, odds_rows: list[dict], fighter_candidates: dict[str, int]) -> None:
    now = datetime.now(timezone.utc)
    rows_by_matchup: dict[int, list[dict]] = {}
    for row in odds_rows:
        rows_by_matchup.setdefault(row["matchup_id"], []).append(row)

    for rows in rows_by_matchup.values():
        resolved = {row["fighter_name"]: best_fighter_match(row["fighter_name"], fighter_candidates) for row in rows}
        fighter_ids = {fid for fid in resolved.values() if fid is not None}
        if len(fighter_ids) != 2:
            continue
        fight = get_fight_by_fighter_pair(session, *fighter_ids)
        if not fight:
            continue
        session.add_all(
            FightOdds(
                fight_id=fight.id,
                fighter_id=resolved[row["fighter_name"]],
                sportsbook=row["sportsbook"],
                moneyline=row["moneyline"],
                scraped_at=now,
            )
            for row in rows
        )
