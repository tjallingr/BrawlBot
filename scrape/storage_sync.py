from datetime import datetime, timezone

from sqlalchemy import and_, or_, select

from data.storage.models import Event, Fight, FightOdds, FightRoundStats, Fighter
from scrape.reconcile.name_match import best_fighter_match, normalize_name


def store_fighter(session, fighter_data: dict) -> Fighter:
    fighter = Fighter(
        ufcstats_id=fighter_data["ufcstats_id"],
        name_raw=fighter_data["name_raw"],
        name_normalized=normalize_name(fighter_data["name_raw"]),
        dob=fighter_data.get("dob"),
        height_cm=fighter_data.get("height_cm"),
        reach_cm=fighter_data.get("reach_cm"),
        stance=fighter_data.get("stance"),
        raw_html_path=fighter_data.get("raw_html_path"),
    )
    session.add(fighter)
    session.flush()
    return fighter


def store_event(session, event_data: dict, fighter_ids: dict[str, int]) -> tuple[Event, list[Fight]]:
    event = Event(
        source="ufcstats",
        source_event_id=event_data["source_event_id"],
        name=event_data["name"],
        date=event_data["date"],
        location=event_data.get("location"),
        raw_html_path=event_data.get("raw_html_path"),
    )
    session.add(event)
    session.flush()

    fights = []
    for fight_data in event_data["fights"]:
        winner_ufcstats_id = fight_data["winner_ufcstats_id"]
        fight = Fight(
            event_id=event.id,
            ufcstats_id=fight_data["ufcstats_fight_id"],
            fighter_a_id=fighter_ids[fight_data["fighter_a_ufcstats_id"]],
            fighter_b_id=fighter_ids[fight_data["fighter_b_ufcstats_id"]],
            winner_id=fighter_ids.get(winner_ufcstats_id) if winner_ufcstats_id else None,
            weight_class=fight_data["weight_class"],
            method=fight_data["method"],
            round=fight_data["round"],
            time=fight_data["time"],
            kd_a=fight_data["kd_a"],
            kd_b=fight_data["kd_b"],
            str_a=fight_data["str_a"],
            str_b=fight_data["str_b"],
            td_a=fight_data["td_a"],
            td_b=fight_data["td_b"],
            sub_a=fight_data["sub_a"],
            sub_b=fight_data["sub_b"],
        )
        session.add(fight)
        fights.append(fight)
    session.flush()
    return event, fights


def store_round_stats(session, fight: Fight, round_stats: list[dict], fighter_ids: dict[str, int]) -> None:
    for row in round_stats:
        session.add(
            FightRoundStats(
                fight_id=fight.id,
                fighter_id=fighter_ids[row["fighter_ufcstats_id"]],
                round=row["round"],
                kd=row["kd"],
                sig_str_landed=row["sig_str_landed"],
                sig_str_att=row["sig_str_att"],
                total_str_landed=row["total_str_landed"],
                total_str_att=row["total_str_att"],
                td_landed=row["td_landed"],
                td_att=row["td_att"],
                sub_att=row["sub_att"],
                rev=row["rev"],
                ctrl_time_sec=row["ctrl_time_sec"],
                sig_str_head=row["sig_str_head"],
                sig_str_body=row["sig_str_body"],
                sig_str_leg=row["sig_str_leg"],
                sig_str_distance=row["sig_str_distance"],
                sig_str_clinch=row["sig_str_clinch"],
                sig_str_ground=row["sig_str_ground"],
            )
        )


def _find_fight_by_fighter_pair(session, fighter_a_id: int, fighter_b_id: int) -> Fight | None:
    return session.execute(
        select(Fight).where(
            or_(
                and_(Fight.fighter_a_id == fighter_a_id, Fight.fighter_b_id == fighter_b_id),
                and_(Fight.fighter_a_id == fighter_b_id, Fight.fighter_b_id == fighter_a_id),
            )
        )
    ).scalars().first()


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
        fighter_a_id, fighter_b_id = fighter_ids
        fight = _find_fight_by_fighter_pair(session, fighter_a_id, fighter_b_id)
        if not fight:
            continue
        for row in rows:
            fighter_id = resolved[row["fighter_name"]]
            session.add(
                FightOdds(
                    fight_id=fight.id,
                    fighter_id=fighter_id,
                    sportsbook=row["sportsbook"],
                    moneyline=row["moneyline"],
                    scraped_at=now,
                )
            )
