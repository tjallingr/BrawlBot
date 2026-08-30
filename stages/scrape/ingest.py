from datetime import datetime, timezone

from core.name_match import best_fighter_match, normalize_name
from data.storage.repositories import events as event_repo
from data.storage.repositories import fight_odds as odds_repo
from data.storage.repositories import fighters as fighter_repo
from data.storage.repositories import fights as fight_repo


def store_fighter(session, fighter_data: dict):
    return fighter_repo.add(
        session,
        ufcstats_id=fighter_data["ufcstats_id"],
        name_raw=fighter_data["name_raw"],
        name_normalized=normalize_name(fighter_data["name_raw"]),
        dob=fighter_data.get("dob"),
        height_cm=fighter_data.get("height_cm"),
        reach_cm=fighter_data.get("reach_cm"),
        stance=fighter_data.get("stance"),
        raw_html_path=fighter_data.get("raw_html_path"),
    )


def store_event(session, event_data: dict, fighter_ids: dict[str, int]):
    event = event_repo.add(
        session,
        source="ufcstats",
        source_event_id=event_data["source_event_id"],
        name=event_data["name"],
        date=event_data["date"],
        location=event_data.get("location"),
        raw_html_path=event_data.get("raw_html_path"),
    )
    fights = fight_repo.add_all(
        session,
        [
            {
                **fight_data,
                "event_id": event.id,
                "ufcstats_id": fight_data["ufcstats_fight_id"],
                "fighter_a_id": fighter_ids[fight_data["fighter_a_ufcstats_id"]],
                "fighter_b_id": fighter_ids[fight_data["fighter_b_ufcstats_id"]],
                "winner_id": fighter_ids.get(fight_data["winner_ufcstats_id"]),
            }
            for fight_data in event_data["fights"]
        ],
    )
    return event, fights


def store_fight_details(session, fight, fight_details: dict, raw_html_path: str, fighter_ids: dict[str, int]) -> None:
    fight_repo.update(
        session,
        fight,
        raw_html_path=raw_html_path,
        is_title_fight=fight_details["is_title_fight"],
        method_detail=fight_details["method_detail"],
    )
    fight_repo.add_round_stats(
        session,
        [
            {
                **row,
                "fight_id": fight.id,
                "fighter_id": fighter_ids[row["fighter_ufcstats_id"]],
            }
            for row in fight_details["round_stats"]
        ],
    )


def store_fight_odds(session, odds_rows: list[dict], fighter_candidates: dict[str, int]) -> None:
    now = datetime.now(timezone.utc)
    rows_by_matchup: dict[int, list[dict]] = {}
    for row in odds_rows:
        rows_by_matchup.setdefault(row["matchup_id"], []).append(row)

    for rows in rows_by_matchup.values():
        names = {row["fighter_name"] for row in rows}
        resolved = {name: best_fighter_match(name, fighter_candidates) for name in names}
        fighter_ids = {fid for fid in resolved.values() if fid is not None}
        if len(fighter_ids) != 2:
            continue
        fight = fight_repo.get_by_fighter_pair(session, *fighter_ids)
        if not fight:
            continue
        odds_repo.add_all(
            session,
            [
                {
                    "fight_id": fight.id,
                    "fighter_id": resolved[row["fighter_name"]],
                    "sportsbook": row["sportsbook"],
                    "moneyline": row["moneyline"],
                    "scraped_at": now,
                }
                for row in rows
            ],
        )
