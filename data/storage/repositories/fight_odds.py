from data.storage.models import FightOdds


def add_all(session, rows: list[dict]) -> None:
    session.add_all(FightOdds(**row) for row in rows)
