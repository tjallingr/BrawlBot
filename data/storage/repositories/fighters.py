from data.storage.models import Fighter
from scrape.reconcile.name_match import normalize_name


def get_all_fighters():
    pass


def get_fighter_stats(fighter):
    pass


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
