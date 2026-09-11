from sqlalchemy.dialects.sqlite import insert

from data.storage.models import FightOdds


def add_all(session, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = insert(FightOdds)
    stmt = stmt.on_conflict_do_update(
        index_elements=["fight_id", "fighter_id", "sportsbook"],
        set_={"moneyline": stmt.excluded.moneyline, "scraped_at": stmt.excluded.scraped_at},
    )
    session.execute(stmt, rows)
