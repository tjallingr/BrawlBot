from datetime import datetime

from data.storage.models import ScrapeCheckpoint


def mark_run(session, source: str, at: datetime) -> None:
    session.merge(ScrapeCheckpoint(source=source, last_run_at=at))
