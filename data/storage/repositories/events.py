from sqlalchemy import select

from data.storage.models import Event, Fight
from data.storage.repositories import model_kwargs


def get_all_events(session) -> list[Event]:
    return list(session.execute(select(Event).order_by(Event.date)).scalars())


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

    fights = [
        Fight(
            event_id=event.id,
            ufcstats_id=fight_data["ufcstats_fight_id"],
            fighter_a_id=fighter_ids[fight_data["fighter_a_ufcstats_id"]],
            fighter_b_id=fighter_ids[fight_data["fighter_b_ufcstats_id"]],
            winner_id=fighter_ids.get(fight_data["winner_ufcstats_id"]),
            **model_kwargs(Fight, fight_data),
        )
        for fight_data in event_data["fights"]
    ]
    session.add_all(fights)
    session.flush()
    return event, fights
