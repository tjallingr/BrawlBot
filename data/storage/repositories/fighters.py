from sqlalchemy import select

from data.storage.models import Fighter


def add(session, **fields) -> Fighter:
    fighter = Fighter(**fields)
    session.add(fighter)
    session.flush()
    return fighter


def get_all(session) -> dict[int, Fighter]:
    return {fighter.id: fighter for fighter in session.execute(select(Fighter)).scalars()}


def get_ufcstats_ids(session) -> dict[str, int]:
    return dict(session.execute(
        select(Fighter.ufcstats_id, Fighter.id).where(Fighter.ufcstats_id.is_not(None))
    ).all())


def get_normalized_names(session) -> dict[str, int]:
    return dict(session.execute(select(Fighter.name_normalized, Fighter.id)).all())
