from datetime import date

from sqlalchemy import and_, or_, select

from data.storage.mapping import column_names, model_kwargs
from data.storage.models import Event, Fight, FightRoundStats

# Everything FightRoundStats counts per round; summing them describes a whole fight.
ROUND_STAT_COLUMNS = column_names(FightRoundStats, exclude={"id", "fight_id", "fighter_id", "round"})


def add_all(session, rows: list[dict]) -> list[Fight]:
    fights = [Fight(**model_kwargs(Fight, row)) for row in rows]
    session.add_all(fights)
    session.flush()
    return fights


def update(session, fight: Fight, **fields) -> Fight:
    for name, value in fields.items():
        setattr(fight, name, value)
    return fight


def get_by_fighter_pair(
    session, fighter_a_id: int, fighter_b_id: int, month: int | None = None, day: int | None = None
) -> Fight | None:
    # two fighters can meet more than once (trilogies aren't rare in MMA), so
    candidates = session.execute(
        select(Fight, Event.date)
        .join(Event, Event.id == Fight.event_id)
        .where(
            or_(
                and_(Fight.fighter_a_id == fighter_a_id, Fight.fighter_b_id == fighter_b_id),
                and_(Fight.fighter_a_id == fighter_b_id, Fight.fighter_b_id == fighter_a_id),
            )
        )
    ).all()
    if not candidates:
        return None
    if month is None or day is None:
        return candidates[0][0]
    for fight, event_date in candidates:
        if event_date.month == month and event_date.day == day:
            return fight
    return None


def get_all_with_dates(session) -> list[tuple[Fight, date]]:
    return session.execute(
        select(Fight, Event.date).join(Event, Event.id == Fight.event_id).order_by(Event.date, Fight.id)
    ).all()


def add_round_stats(session, rows: list[dict]) -> None:
    """Insert round stats. Keys that are not columns of the table are ignored."""
    session.add_all(FightRoundStats(**model_kwargs(FightRoundStats, row)) for row in rows)


def get_all_round_stats(session) -> list[FightRoundStats]:
    return list(session.execute(select(FightRoundStats)).scalars())
