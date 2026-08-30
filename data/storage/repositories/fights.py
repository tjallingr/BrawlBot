from sqlalchemy import and_, func, or_, select

from data.storage.models import Event, Fight, FightRoundStats
from data.storage.repositories import model_kwargs


ROUND_STAT_COLUMNS = tuple(
    column.name
    for column in FightRoundStats.__table__.columns
    if column.name not in {"id", "fight_id", "fighter_id", "round"}
)


def get_fights_chronological(session) -> list[tuple[Fight, object]]:
    return session.execute(
        select(Fight, Event.date)
        .join(Event, Event.id == Fight.event_id)
        .where(Fight.winner_id.is_not(None))
        .order_by(Event.date, Fight.id)
    ).all()


def get_fight_stats(session) -> dict[tuple[int, int], dict[str, int]]:
    totals = [func.sum(getattr(FightRoundStats, name)).label(name) for name in ROUND_STAT_COLUMNS]
    rows = session.execute(
        select(FightRoundStats.fight_id, FightRoundStats.fighter_id, *totals)
        .group_by(FightRoundStats.fight_id, FightRoundStats.fighter_id)
    ).all()
    return {
        (row.fight_id, row.fighter_id): {name: getattr(row, name) for name in ROUND_STAT_COLUMNS}
        for row in rows
    }


def get_rounds_per_fight(session) -> dict[int, int]:
    rows = session.execute(
        select(FightRoundStats.fight_id, func.max(FightRoundStats.round)).group_by(FightRoundStats.fight_id)
    ).all()
    return dict(rows)


def get_fight_by_fighter_pair(session, fighter_a_id: int, fighter_b_id: int) -> Fight | None:
    return session.execute(
        select(Fight).where(
            or_(
                and_(Fight.fighter_a_id == fighter_a_id, Fight.fighter_b_id == fighter_b_id),
                and_(Fight.fighter_a_id == fighter_b_id, Fight.fighter_b_id == fighter_a_id),
            )
        )
    ).scalars().first()


def store_round_stats(session, fight: Fight, round_stats: list[dict], fighter_ids: dict[str, int]) -> None:
    session.add_all(
        FightRoundStats(
            fight_id=fight.id,
            fighter_id=fighter_ids[row["fighter_ufcstats_id"]],
            **model_kwargs(FightRoundStats, row),
        )
        for row in round_stats
    )
