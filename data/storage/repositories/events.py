from sqlalchemy import select

from data.storage.models import Event


def add(session, **fields) -> Event:
    event = Event(**fields)
    session.add(event)
    session.flush()
    return event


def get_all(session) -> list[Event]:
    return list(session.execute(select(Event).order_by(Event.date)).scalars())


def get_source_ids(session, source: str) -> set[str]:
    return {row.source_event_id for row in session.execute(
        select(Event.source_event_id).where(Event.source == source)
    )}
