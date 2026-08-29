from sqlalchemy import and_, or_, select

from data.storage.models import Fight, FightRoundStats
from data.storage.repositories import model_kwargs


def get_fight_stats(fight):
    pass


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
